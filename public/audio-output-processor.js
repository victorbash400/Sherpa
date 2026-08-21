class AudioOutputProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.inputSampleRate = 24000;
    this.minimumBufferedSamples = Math.round(this.inputSampleRate * 0.12);
    this.capacity = this.inputSampleRate * 30;
    this.buffer = new Float32Array(this.capacity);
    this.readIndex = 0;
    this.writeIndex = 0;
    this.available = 0;
    this.playing = false;
    this.turnComplete = false;
    this.phase = 0;
    this.currentSample = 0;
    this.nextSample = 0;

    this.port.onmessage = ({ data }) => {
      if (data.type === "audio") this.enqueue(new Int16Array(data.pcm));
      if (data.type === "turn_complete") {
        this.turnComplete = true;
        if (!this.playing && this.available < 2) {
          this.turnComplete = false;
          this.port.postMessage({ type: "drained" });
        }
      }
      if (data.type === "reset") this.reset();
    };
  }

  enqueue(pcm) {
    this.turnComplete = false;
    for (let index = 0; index < pcm.length; index += 1) {
      if (this.available === this.capacity) {
        this.readIndex = (this.readIndex + 1) % this.capacity;
        this.available -= 1;
      }
      this.buffer[this.writeIndex] = pcm[index] / 32768;
      this.writeIndex = (this.writeIndex + 1) % this.capacity;
      this.available += 1;
    }
  }

  readSample() {
    if (!this.available) return undefined;
    const sample = this.buffer[this.readIndex];
    this.readIndex = (this.readIndex + 1) % this.capacity;
    this.available -= 1;
    return sample;
  }

  reset() {
    this.readIndex = 0;
    this.writeIndex = 0;
    this.available = 0;
    this.playing = false;
    this.turnComplete = false;
    this.phase = 0;
    this.currentSample = 0;
    this.nextSample = 0;
  }

  startIfReady() {
    const required = this.turnComplete ? 2 : this.minimumBufferedSamples;
    if (this.playing || this.available < required) return;
    this.currentSample = this.readSample() ?? 0;
    this.nextSample = this.readSample() ?? this.currentSample;
    this.phase = 0;
    this.playing = true;
  }

  process(_inputs, outputs) {
    const output = outputs[0][0];
    output.fill(0);
    this.startIfReady();
    if (!this.playing) return true;

    const ratio = this.inputSampleRate / sampleRate;
    for (let index = 0; index < output.length; index += 1) {
      output[index] = this.currentSample
        + (this.nextSample - this.currentSample) * this.phase;
      this.phase += ratio;
      while (this.phase >= 1) {
        const sample = this.readSample();
        if (sample === undefined) {
          this.playing = false;
          if (this.turnComplete) {
            this.turnComplete = false;
            this.port.postMessage({ type: "drained" });
          } else {
            this.port.postMessage({ type: "underrun" });
          }
          return true;
        }
        this.currentSample = this.nextSample;
        this.nextSample = sample;
        this.phase -= 1;
      }
    }
    return true;
  }
}

registerProcessor("audio-output-processor", AudioOutputProcessor);
