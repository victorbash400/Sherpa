import { useCallback, useEffect, useRef, useState } from "react";

export function useVoicePreview(volume: number, speakerMuted: boolean) {
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState<string>();
  const socketRef = useRef<WebSocket | undefined>(undefined);
  const contextRef = useRef<AudioContext | undefined>(undefined);
  const sourcesRef = useRef(new Set<AudioBufferSourceNode>());
  const playheadRef = useRef(0);

  const stop = useCallback(() => {
    socketRef.current?.close();
    socketRef.current = undefined;
    for (const source of sourcesRef.current) source.stop();
    sourcesRef.current.clear();
    const context = contextRef.current;
    contextRef.current = undefined;
    if (context && context.state !== "closed") void context.close();
    setPlaying(false);
  }, []);

  const preview = useCallback(async (voiceName: string) => {
    stop();
    setPlaying(true);
    setError(undefined);
    try {
      const context = new AudioContext();
      contextRef.current = context;
      playheadRef.current = context.currentTime;
      const socket = new WebSocket(`ws://127.0.0.1:8000/voice/${crypto.randomUUID()}?voice=${encodeURIComponent(voiceName)}`);
      socket.binaryType = "arraybuffer";
      socketRef.current = socket;
      socket.addEventListener("message", (event) => {
        if (event.data instanceof ArrayBuffer) {
          const pcm = new Int16Array(event.data);
          const buffer = context.createBuffer(1, pcm.length, 24000);
          const channel = buffer.getChannelData(0);
          for (let index = 0; index < pcm.length; index += 1) channel[index] = pcm[index] / 32768;
          const source = context.createBufferSource();
          const gain = context.createGain();
          gain.gain.value = speakerMuted ? 0 : volume / 100;
          source.buffer = buffer;
          source.connect(gain).connect(context.destination);
          const startsAt = Math.max(context.currentTime, playheadRef.current);
          playheadRef.current = startsAt + buffer.duration;
          sourcesRef.current.add(source);
          source.addEventListener("ended", () => sourcesRef.current.delete(source), { once: true });
          source.start(startsAt);
          return;
        }
        const message = JSON.parse(String(event.data)) as { type: string; error?: string };
        if (message.type === "ready") socket.send(JSON.stringify({ type: "preview" }));
        if (message.type === "turn_complete") {
          const remaining = Math.max(0, playheadRef.current - context.currentTime) * 1000;
          window.setTimeout(stop, remaining);
        }
        if (message.type === "error") {
          setError(message.error || "Voice preview failed.");
          stop();
        }
      });
      socket.addEventListener("error", () => {
        setError("Voice preview failed.");
        stop();
      }, { once: true });
    } catch (reason) {
      stop();
      setError(reason instanceof Error ? reason.message : "Voice preview failed.");
    }
  }, [speakerMuted, stop, volume]);

  useEffect(() => stop, [stop]);
  return { error, playing, preview, stop };
}
