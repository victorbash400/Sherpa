class AudioInputProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.phase = 0;
    this.ratio = sampleRate / 16000;
    this.samples = [];
  }

  process(inputs) {
    const channel = inputs[0]?.[0];
    if (!channel) return true;

    for (let index = 0; index < channel.length; index += 1) {
      if (this.phase <= 0) {
        this.samples.push(Math.max(-1, Math.min(1, channel[index])));
        this.phase += this.ratio;
      }
      this.phase -= 1;
    }

    while (this.samples.length >= 320) {
      const pcm = new Int16Array(320);
      for (let index = 0; index < pcm.length; index += 1) {
        const sample = this.samples[index];
        pcm[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
      }
      this.samples.splice(0, pcm.length);
      this.port.postMessage(pcm.buffer, [pcm.buffer]);
    }
    return true;
  }
}

registerProcessor("audio-input-processor", AudioInputProcessor);
