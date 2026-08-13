import { useCallback, useEffect, useRef, useState } from "react";

export type VoiceStatus = "idle" | "connecting" | "listening" | "speaking" | "error";

interface VoiceSessionOptions {
  microphoneMuted: boolean;
  sessionId: string;
  speakerMuted: boolean;
  volume: number;
  voiceName: string;
}

export function useVoiceSession({ microphoneMuted, sessionId, speakerMuted, volume, voiceName }: VoiceSessionOptions) {
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [audioLevel, setAudioLevel] = useState(0);
  const [error, setError] = useState<string>();
  const socketRef = useRef<WebSocket | undefined>(undefined);
  const streamRef = useRef<MediaStream | undefined>(undefined);
  const contextRef = useRef<AudioContext | undefined>(undefined);
  const inputNodeRef = useRef<AudioWorkletNode | undefined>(undefined);
  const gainRef = useRef<GainNode | undefined>(undefined);
  const sourcesRef = useRef(new Set<AudioBufferSourceNode>());
  const playheadRef = useRef(0);
  const mutedRef = useRef(microphoneMuted);

  mutedRef.current = microphoneMuted;

  const clearPlayback = useCallback(() => {
    for (const source of sourcesRef.current) source.stop();
    sourcesRef.current.clear();
    playheadRef.current = contextRef.current?.currentTime ?? 0;
    setAudioLevel(0);
  }, []);

  const stop = useCallback(() => {
    socketRef.current?.close();
    socketRef.current = undefined;
    inputNodeRef.current?.disconnect();
    inputNodeRef.current = undefined;
    for (const track of streamRef.current?.getTracks() ?? []) track.stop();
    streamRef.current = undefined;
    clearPlayback();
    const context = contextRef.current;
    contextRef.current = undefined;
    gainRef.current = undefined;
    if (context && context.state !== "closed") void context.close();
    setStatus("idle");
  }, [clearPlayback]);

  const playAudio = useCallback((data: ArrayBuffer) => {
    const context = contextRef.current;
    const gain = gainRef.current;
    if (!context || !gain) return;
    const pcm = new Int16Array(data);
    const audioBuffer = context.createBuffer(1, pcm.length, 24000);
    const output = audioBuffer.getChannelData(0);
    let sum = 0;
    for (let index = 0; index < pcm.length; index += 1) {
      const sample = pcm[index] / 32768;
      output[index] = sample;
      sum += sample * sample;
    }
    setAudioLevel(Math.min(1, Math.sqrt(sum / Math.max(1, pcm.length)) * 4));
    const source = context.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(gain);
    const startsAt = Math.max(context.currentTime, playheadRef.current);
    playheadRef.current = startsAt + audioBuffer.duration;
    sourcesRef.current.add(source);
    source.addEventListener("ended", () => sourcesRef.current.delete(source), { once: true });
    source.start(startsAt);
    setStatus("speaking");
  }, []);

  const start = useCallback(async () => {
    if (status !== "idle" && status !== "error") return;
    setStatus("connecting");
    setError(undefined);
    try {
      const socket = new WebSocket(`ws://127.0.0.1:8000/voice/${sessionId}?voice=${encodeURIComponent(voiceName)}`);
      socket.binaryType = "arraybuffer";
      socketRef.current = socket;
      await new Promise<void>((resolve, reject) => {
        const fail = () => reject(new Error("Could not connect to Sherpa voice."));
        const ready = (event: MessageEvent) => {
          if (typeof event.data !== "string") return;
          const message = JSON.parse(event.data) as { type: string; error?: string };
          if (message.type === "ready") {
            socket.removeEventListener("message", ready);
            resolve();
          } else if (message.type === "error") {
            socket.removeEventListener("message", ready);
            reject(new Error(message.error || "Sherpa voice failed."));
          }
        };
        socket.addEventListener("message", ready);
        socket.addEventListener("error", fail, { once: true });
      });

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { autoGainControl: true, echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = stream;
      const context = new AudioContext();
      contextRef.current = context;
      const gain = context.createGain();
      gain.gain.value = speakerMuted ? 0 : volume / 100;
      gain.connect(context.destination);
      gainRef.current = gain;
      await context.audioWorklet.addModule("/audio-input-processor.js");

      const source = context.createMediaStreamSource(stream);
      const inputNode = new AudioWorkletNode(context, "audio-input-processor");
      const silentGain = context.createGain();
      silentGain.gain.value = 0;
      source.connect(inputNode);
      inputNode.connect(silentGain).connect(context.destination);
      inputNode.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
        if (!mutedRef.current && socket.readyState === WebSocket.OPEN) socket.send(event.data);
      };
      inputNodeRef.current = inputNode;

      socket.addEventListener("message", (event) => {
        if (event.data instanceof ArrayBuffer) {
          playAudio(event.data);
          return;
        }
        const message = JSON.parse(String(event.data)) as { type: string; error?: string };
        if (message.type === "interrupted") {
          clearPlayback();
          setStatus("listening");
        } else if (message.type === "turn_complete") {
          setStatus("listening");
          setAudioLevel(0);
        } else if (message.type === "error") {
          setError(message.error || "Sherpa voice failed.");
          setStatus("error");
        }
      });
      socket.addEventListener("close", () => {
        if (socketRef.current === socket) stop();
      });
      setStatus("listening");
    } catch (reason) {
      stop();
      setError(reason instanceof Error ? reason.message : "Sherpa voice failed.");
      setStatus("error");
    }
  }, [clearPlayback, playAudio, sessionId, speakerMuted, status, stop, voiceName, volume]);

  useEffect(() => {
    if (gainRef.current) gainRef.current.gain.value = speakerMuted ? 0 : volume / 100;
  }, [speakerMuted, volume]);

  useEffect(() => stop, [stop]);

  return { audioLevel, error, start, status, stop };
}
