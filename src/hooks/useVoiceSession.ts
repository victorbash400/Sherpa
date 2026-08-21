import { useCallback, useEffect, useRef, useState } from "react";
import type { VoiceTranscriptEntry } from "../chat/chatTypes";
import type { PreviewCursor, PreviewTarget } from "../types/sherpaOverlay";

export type VoiceStatus = "idle" | "connecting" | "listening" | "speaking" | "error";
export type PhotoCaptureRequest = { callId: string };
export type PhotoCaptureResult = {
  status: "captured" | "failed";
  path?: string;
  mimeType?: string;
  error?: string;
};
export type VoiceToolActivity = {
  id: string;
  name: string;
  args: Record<string, unknown>;
  status: "running" | "done" | "error";
  error?: string;
};
export type VoiceContextUsage = {
  tokens: number | null;
  limit: number;
  compacting: boolean;
};
export type TaskApiActivity = {
  id: string;
  message: string;
  tool: string;
};
export type VoiceTask = {
  id: string;
  chatId: string;
  instruction: string;
  kind: "worker";
  parentId?: string;
  status: "queued" | "running" | "blocked" | "completed" | "failed" | "cancelled";
  phase: string;
  progress: number;
  currentStep: string;
  updates: VoiceTaskUpdate[];
  result?: string;
  previewTarget?: PreviewTarget;
  interactionMode?: "background" | "foreground";
  previewCursor?: PreviewCursor;
  previewRevision?: string;
  apiActivity?: TaskApiActivity;
};
export type VoiceTaskUpdate = {
  phase: string;
  progress: number;
  message: string;
  nextStep: string;
  createdAt: string;
};

type TaskPayload = {
  task_id?: string;
  chat_id?: string;
  instruction?: string;
  kind?: VoiceTask["kind"];
  parent_id?: string | null;
  status?: VoiceTask["status"];
  phase?: string;
  progress?: number;
  current_step?: string;
  summary?: string;
  preview_target?: PreviewTarget;
  interaction_mode?: VoiceTask["interactionMode"];
  updates?: Array<{ phase: string; progress: number; message: string; next_step?: string; created_at: string }>;
  context_tokens?: number;
  context_token_limit?: number;
};

interface VoiceSessionOptions {
  microphoneMuted: boolean;
  sessionId: string;
  speakerMuted: boolean;
  spokenLanguage: string;
  volume: number;
  voiceName: string;
  onTranscript: (entry: VoiceTranscriptEntry) => void;
  onTurnComplete: () => void;
}

export function useVoiceSession({ microphoneMuted, onTranscript, onTurnComplete, sessionId, speakerMuted, spokenLanguage, volume, voiceName }: VoiceSessionOptions) {
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [audioLevel, setAudioLevel] = useState(0);
  const [error, setError] = useState<string>();
  const [toolActivities, setToolActivities] = useState<VoiceToolActivity[]>([]);
  const [contextUsage, setContextUsage] = useState<VoiceContextUsage>({
    tokens: null,
    limit: 300_000,
    compacting: false,
  });
  const [tasks, setTasks] = useState<VoiceTask[]>([]);
  const [computerActive, setComputerActive] = useState(false);
  const [photoCaptureRequest, setPhotoCaptureRequest] = useState<PhotoCaptureRequest>();
  const socketRef = useRef<WebSocket | undefined>(undefined);
  const streamRef = useRef<MediaStream | undefined>(undefined);
  const contextRef = useRef<AudioContext | undefined>(undefined);
  const inputNodeRef = useRef<AudioWorkletNode | undefined>(undefined);
  const gainRef = useRef<GainNode | undefined>(undefined);
  const sourcesRef = useRef(new Set<AudioBufferSourceNode>());
  const playheadRef = useRef(0);
  const fadeTimerRef = useRef<number | undefined>(undefined);
  const activityTimerRef = useRef<number | undefined>(undefined);
  const readySoundRef = useRef<HTMLAudioElement | undefined>(undefined);
  const speechEndTimerRef = useRef<number | undefined>(undefined);
  const speechActiveRef = useRef(false);
  const turnCompleteRef = useRef(true);
  const mutedRef = useRef(microphoneMuted);
  const runningTaskIdsRef = useRef(new Set<string>());
  const playbackChunkCountRef = useRef(0);
  const playbackByteCountRef = useRef(0);

  mutedRef.current = microphoneMuted;

  const clearPlayback = useCallback(() => {
    if (fadeTimerRef.current !== undefined) window.clearTimeout(fadeTimerRef.current);
    fadeTimerRef.current = undefined;
    for (const source of sourcesRef.current) source.stop();
    sourcesRef.current.clear();
    playheadRef.current = contextRef.current?.currentTime ?? 0;
    setAudioLevel(0);
  }, []);

  const debugPlayback = useCallback((event: string, details: Record<string, unknown> = {}) => {
    window.sherpaSystem?.debugVoice({ event, sessionId, ...details });
  }, [sessionId]);

  const sendControl = useCallback((type: "playback_drained" | "speech_started" | "speech_ended") => {
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type }));
  }, []);

  const interruptPlayback = useCallback(() => {
    const context = contextRef.current;
    const gain = gainRef.current;
    if (!context || !gain || !sourcesRef.current.size) {
      debugPlayback("interrupted", {
        contextState: context?.state || "missing",
        queuedSources: sourcesRef.current.size,
      });
      clearPlayback();
      playbackChunkCountRef.current = 0;
      playbackByteCountRef.current = 0;
      return;
    }
    debugPlayback("interrupted", {
      contextState: context.state,
      queuedSources: sourcesRef.current.size,
    });
    if (fadeTimerRef.current !== undefined) window.clearTimeout(fadeTimerRef.current);
    const now = context.currentTime;
    gain.gain.cancelScheduledValues(now);
    gain.gain.setValueAtTime(gain.gain.value, now);
    gain.gain.linearRampToValueAtTime(0, now + 0.045);
    fadeTimerRef.current = window.setTimeout(() => {
      for (const source of sourcesRef.current) source.stop();
      sourcesRef.current.clear();
      playheadRef.current = context.currentTime;
      playbackChunkCountRef.current = 0;
      playbackByteCountRef.current = 0;
      gain.gain.cancelScheduledValues(context.currentTime);
      gain.gain.setValueAtTime(speakerMuted ? 0 : volume / 100, context.currentTime);
      fadeTimerRef.current = undefined;
      setAudioLevel(0);
    }, 45);
  }, [clearPlayback, debugPlayback, speakerMuted, volume]);

  const stop = useCallback(() => {
    window.sherpaPreview?.stopAll();
    if (activityTimerRef.current !== undefined) window.clearTimeout(activityTimerRef.current);
    activityTimerRef.current = undefined;
    if (speechEndTimerRef.current !== undefined) window.clearTimeout(speechEndTimerRef.current);
    speechEndTimerRef.current = undefined;
    speechActiveRef.current = false;
    turnCompleteRef.current = true;
    readySoundRef.current?.pause();
    readySoundRef.current = undefined;
    playbackChunkCountRef.current = 0;
    playbackByteCountRef.current = 0;
    if (!runningTaskIdsRef.current.size) {
      window.sherpaOverlay?.hide("voice-session");
      setComputerActive(false);
    }
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
    setToolActivities([]);
    setPhotoCaptureRequest(undefined);
  }, [clearPlayback]);

  const playAudio = useCallback((data: ArrayBuffer) => {
    const context = contextRef.current;
    const gain = gainRef.current;
    playbackChunkCountRef.current += 1;
    playbackByteCountRef.current += data.byteLength;
    if (playbackChunkCountRef.current === 1) {
      debugPlayback("first_chunk_received", {
        bytes: data.byteLength,
        contextState: context?.state || "missing",
        speakerMuted,
        volume,
      });
    }
    if (!context || !gain) {
      debugPlayback("chunk_dropped", {
        bytes: data.byteLength,
        contextState: context?.state || "missing",
        reason: !context ? "missing_context" : "missing_gain",
      });
      return;
    }
    const schedule = () => {
      if (contextRef.current !== context || gainRef.current !== gain) return;
      if (fadeTimerRef.current !== undefined) {
        window.clearTimeout(fadeTimerRef.current);
        fadeTimerRef.current = undefined;
        gain.gain.cancelScheduledValues(context.currentTime);
        gain.gain.setValueAtTime(speakerMuted ? 0 : volume / 100, context.currentTime);
      }
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
      source.addEventListener("ended", () => {
        sourcesRef.current.delete(source);
        if (!sourcesRef.current.size && turnCompleteRef.current) {
          debugPlayback("drained", {
            bytes: playbackByteCountRef.current,
            chunks: playbackChunkCountRef.current,
            contextState: context.state,
          });
          playbackChunkCountRef.current = 0;
          playbackByteCountRef.current = 0;
          sendControl("playback_drained");
        }
      }, { once: true });
      source.start(startsAt);
      setStatus("speaking");
    };
    if (context.state === "suspended") {
      debugPlayback("context_resume_requested", { queuedSources: sourcesRef.current.size });
      void context.resume().then(schedule).catch((reason: unknown) => {
        debugPlayback("context_resume_failed", {
          error: reason instanceof Error ? reason.message : String(reason),
        });
        setError(reason instanceof Error ? reason.message : "Sherpa audio playback could not resume.");
      });
      return;
    }
    if (context.state !== "running") {
      debugPlayback("chunk_dropped", {
        bytes: data.byteLength,
        contextState: context.state,
        reason: "context_not_running",
      });
      setError(`Sherpa audio playback is ${context.state}.`);
      return;
    }
    schedule();
  }, [debugPlayback, sendControl, speakerMuted, volume]);

  const start = useCallback(async () => {
    if (status !== "idle" && status !== "error") return;
    setStatus("connecting");
    setError(undefined);
    try {
      const readySound = new Audio("/47313572-ui-sound-270349.mp3");
      readySound.preload = "auto";
      readySound.volume = speakerMuted ? 0 : volume / 100;
      readySoundRef.current = readySound;
      readySound.load();

      const context = new AudioContext();
      contextRef.current = context;
      const gain = context.createGain();
      gain.gain.value = speakerMuted ? 0 : volume / 100;
      gain.connect(context.destination);
      gainRef.current = gain;
      await context.resume();
      debugPlayback("context_ready", {
        contextState: context.state,
        sampleRate: context.sampleRate,
        speakerMuted,
        volume,
      });
      context.addEventListener("statechange", () => {
        debugPlayback("context_state_changed", { contextState: context.state });
      });

      const query = new URLSearchParams({ voice: voiceName, language: spokenLanguage });
      const socket = new WebSocket(`ws://127.0.0.1:8000/voice/${sessionId}?${query}`);
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
      await context.audioWorklet.addModule("/audio-input-processor.js");

      const source = context.createMediaStreamSource(stream);
      const inputNode = new AudioWorkletNode(context, "audio-input-processor");
      const silentGain = context.createGain();
      silentGain.gain.value = 0;
      source.connect(inputNode);
      inputNode.connect(silentGain).connect(context.destination);
      inputNode.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
        if (mutedRef.current || socket.readyState !== WebSocket.OPEN) return;
        const samples = new Int16Array(event.data);
        let energy = 0;
        for (const sample of samples) energy += (sample / 32768) ** 2;
        const speechDetected = Math.sqrt(energy / Math.max(1, samples.length)) > 0.018;
        if (speechDetected) {
          if (speechEndTimerRef.current !== undefined) window.clearTimeout(speechEndTimerRef.current);
          speechEndTimerRef.current = undefined;
          if (!speechActiveRef.current) {
            speechActiveRef.current = true;
            sendControl("speech_started");
          }
        } else if (speechActiveRef.current && speechEndTimerRef.current === undefined) {
          speechEndTimerRef.current = window.setTimeout(() => {
            speechActiveRef.current = false;
            speechEndTimerRef.current = undefined;
            sendControl("speech_ended");
          }, 500);
        }
        socket.send(event.data);
      };
      inputNodeRef.current = inputNode;

      socket.addEventListener("message", (event) => {
        if (event.data instanceof ArrayBuffer) {
          turnCompleteRef.current = false;
          playAudio(event.data);
          return;
        }
        const message = JSON.parse(String(event.data)) as {
          type: string;
          error?: string;
          text?: string;
          role?: VoiceTranscriptEntry["role"];
          sequence?: number;
          final?: boolean;
          id?: string;
          name?: string;
          args?: Record<string, unknown>;
          result?: { status?: string; error?: string };
          task_id?: string;
          chat_id?: string;
          instruction?: string;
          kind?: VoiceTask["kind"];
          parent_id?: string | null;
          message?: string;
          intent?: string;
          status?: VoiceTask["status"];
          phase?: string;
          progress?: number;
          current_step?: string;
          summary?: string;
          updates?: Array<{
            phase: string;
            progress: number;
            message: string;
            next_step?: string;
            created_at: string;
          }>;
          preview_target?: PreviewTarget;
          interaction_mode?: VoiceTask["interactionMode"];
          context_tokens?: number;
          context_token_limit?: number;
          call_id?: string;
        };
        if (message.type === "capture_photo" && message.call_id) {
          setPhotoCaptureRequest({ callId: message.call_id });
        } else if (message.type === "interrupted") {
          interruptPlayback();
          setStatus("listening");
        } else if (message.type === "turn_complete") {
          debugPlayback("turn_complete", {
            bytes: playbackByteCountRef.current,
            chunks: playbackChunkCountRef.current,
            contextState: contextRef.current?.state || "missing",
            queuedSources: sourcesRef.current.size,
          });
          onTurnComplete();
          turnCompleteRef.current = true;
          if (!sourcesRef.current.size) {
            playbackChunkCountRef.current = 0;
            playbackByteCountRef.current = 0;
            sendControl("playback_drained");
          }
          setStatus("listening");
          setAudioLevel(0);
          if (activityTimerRef.current !== undefined) window.clearTimeout(activityTimerRef.current);
          activityTimerRef.current = window.setTimeout(() => {
            setToolActivities([]);
            activityTimerRef.current = undefined;
          }, 1200);
        } else if (message.type === "error") {
          setError(message.error || "Sherpa voice failed.");
          setStatus("error");
        } else if (
          message.type === "transcript_update"
          && message.id
          && message.role
          && typeof message.sequence === "number"
        ) {
          onTranscript({
            id: message.id,
            role: message.role,
            sequence: message.sequence,
            text: message.text || "",
            final: Boolean(message.final),
          });
        } else if (message.type === "tool_call" && message.id && message.name) {
          const toolId = message.id;
          const toolName = message.name;
          if (activityTimerRef.current !== undefined) window.clearTimeout(activityTimerRef.current);
          activityTimerRef.current = undefined;
          setToolActivities([{
              id: toolId,
              name: toolName,
              args: message.args || {},
              status: "running",
          }]);
          if (message.name.startsWith("computer_") || message.name.startsWith("browser_")) {
            if (message.task_id && message.preview_target) {
              const overlayX = message.args?.overlay_x;
              const overlayY = message.args?.overlay_y;
              setTasks((current) => current.map((task) => task.id === message.task_id
                ? {
                  ...task,
                  previewTarget: message.preview_target,
                  interactionMode: message.interaction_mode || "background",
                  previewRevision: toolId,
                  previewCursor: typeof overlayX === "number" && typeof overlayY === "number" ? {
                    id: toolId,
                    action: toolName,
                    x: overlayX,
                    y: overlayY,
                  } : task.previewCursor,
                }
                : task));
            }
            setComputerActive(true);
            window.sherpaOverlay?.show({
              id: toolId,
              action: message.name,
              message: message.message || toolName.replace(/^(computer|browser)_/, "").replaceAll("_", " "),
              intent: message.intent,
              args: message.args || {},
            });
          } else if (message.task_id) {
            setTasks((current) => current.map((task) => task.id === message.task_id
              ? {
                ...task,
                apiActivity: {
                  id: toolId,
                  message: message.message || toolName.replaceAll("_", " "),
                  tool: toolName,
                },
              }
              : task));
          }
        } else if (message.type === "tool_response" && message.id) {
          setToolActivities((current) => current.map((activity) =>
            activity.id === message.id
              ? {
                ...activity,
                status: message.result?.status === "failed" ? "error" : "done",
                error: message.result?.error,
              }
              : activity,
          ));
          setTasks((current) => current.map((task) => task.apiActivity?.id === message.id
            ? { ...task, apiActivity: undefined, previewRevision: message.id }
            : task));
        } else if (message.type === "context_usage" && typeof message.context_tokens === "number") {
          setContextUsage((current) => ({
            tokens: message.context_tokens ?? current.tokens,
            limit: message.context_token_limit ?? current.limit,
            compacting: current.compacting,
          }));
        } else if (message.type === "compaction_started") {
          setToolActivities([]);
          setContextUsage((current) => ({
            tokens: message.context_tokens ?? current.tokens,
            limit: message.context_token_limit ?? current.limit,
            compacting: true,
          }));
        } else if (message.type === "compaction_completed" || message.type === "compaction_failed") {
          setContextUsage((current) => ({
            tokens: message.type === "compaction_completed" ? null : current.tokens,
            limit: message.context_token_limit ?? current.limit,
            compacting: false,
          }));
        } else if (message.type === "task_started" && message.task_id && message.instruction) {
          runningTaskIdsRef.current.add(message.task_id);
          setTasks((current) => [
            ...current.filter((task) => task.id !== message.task_id),
            taskFromMessage(message, sessionId),
          ]);
        } else if (
          [
            "task_updated",
            "task_question",
            "task_question_answered",
            "task_steering_queued",
            "task_steering_applied",
          ].includes(message.type)
          && message.task_id
          && message.instruction
        ) {
          setTasks((current) => {
            const task = taskFromMessage(message, sessionId);
            return current.some((item) => item.id === task.id)
              ? current.map((item) => item.id === task.id ? {
                ...task,
                previewTarget: task.previewTarget || item.previewTarget,
                interactionMode: item.interactionMode,
                previewCursor: item.previewCursor,
                previewRevision: item.previewRevision,
                apiActivity: item.apiActivity,
              } : item)
              : [...current, task];
          });
        } else if (
          (message.type === "task_completed" || message.type === "task_failed" || message.type === "task_cancelled")
          && message.task_id
        ) {
          window.sherpaPreview?.stop(message.task_id);
          runningTaskIdsRef.current.delete(message.task_id);
          if (!runningTaskIdsRef.current.size) {
            window.sherpaOverlay?.hide(message.task_id);
            setComputerActive(false);
          }
          const taskStatus = message.type.replace("task_", "") as VoiceTask["status"];
          setTasks((current) => current.map((task) => task.id === message.task_id
            ? {
              ...taskFromMessage(message, sessionId),
              previewTarget: task.previewTarget,
              interactionMode: task.interactionMode,
              previewCursor: task.previewCursor,
              previewRevision: task.previewRevision,
              apiActivity: undefined,
              status: taskStatus,
              result: message.message || message.summary,
            }
            : task));
        }
      });
      socket.addEventListener("close", () => {
        if (socketRef.current === socket) stop();
      });
      setStatus("listening");
      if (!speakerMuted) {
        try {
          readySound.currentTime = 0;
          await readySound.play();
        } catch {
          setError("Sherpa is ready, but the readiness sound could not play.");
        }
      }
    } catch (reason) {
      stop();
      setError(reason instanceof Error ? reason.message : "Sherpa voice failed.");
      setStatus("error");
    }
  }, [clearPlayback, debugPlayback, interruptPlayback, onTranscript, onTurnComplete, playAudio, sendControl, sessionId, speakerMuted, spokenLanguage, status, stop, voiceName, volume]);

  const sendVideoFrame = useCallback((data: string, mimeType: string) => {
    const socket = socketRef.current;
    if (socket?.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify({ type: "video_frame", data, mime_type: mimeType }));
  }, []);

  const completePhotoCapture = useCallback((callId: string, result: PhotoCaptureResult) => {
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        type: "photo_capture_result",
        call_id: callId,
        status: result.status,
        path: result.path,
        mime_type: result.mimeType,
        error: result.error,
      }));
    }
    setPhotoCaptureRequest((current) => current?.callId === callId ? undefined : current);
  }, []);

  useEffect(() => {
    if (gainRef.current) gainRef.current.gain.value = speakerMuted ? 0 : volume / 100;
    if (readySoundRef.current) readySoundRef.current.volume = speakerMuted ? 0 : volume / 100;
  }, [speakerMuted, volume]);

  useEffect(() => {
    if (!microphoneMuted || !speechActiveRef.current) return;
    if (speechEndTimerRef.current !== undefined) window.clearTimeout(speechEndTimerRef.current);
    speechEndTimerRef.current = undefined;
    speechActiveRef.current = false;
    sendControl("speech_ended");
  }, [microphoneMuted, sendControl]);

  useEffect(() => {
    const controller = new AbortController();
    void fetch(`http://127.0.0.1:8000/tasks/${encodeURIComponent(sessionId)}`, {
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("Could not load this chat's tasks.");
        return response.json() as Promise<{ tasks: TaskPayload[] }>;
      })
      .then(({ tasks: loadedTasks }) => {
        setTasks((current) => [
          ...current.filter((task) => task.chatId !== sessionId),
          ...loadedTasks.map((task) => taskFromMessage(task, sessionId)),
        ]);
        const activeTask = loadedTasks.find((task) => ["running", "blocked"].includes(task.status || ""));
        setContextUsage({
          tokens: activeTask?.context_tokens || null,
          limit: activeTask?.context_token_limit ?? 300_000,
          compacting: false,
        });
      })
      .catch((reason: unknown) => {
        if (!(reason instanceof DOMException && reason.name === "AbortError")) {
          setError(reason instanceof Error ? reason.message : "Could not load this chat's tasks.");
        }
      });
    return () => controller.abort();
  }, [sessionId]);

  useEffect(() => {
    if (!tasks.some((task) => (
      task.chatId === sessionId
      && ["running", "blocked"].includes(task.status)
      && task.previewTarget
    ))) {
      window.sherpaPreview?.stopAll();
    }
  }, [sessionId, tasks]);

  useEffect(() => stop, [stop]);

  return {
    audioLevel,
    computerActive,
    completePhotoCapture,
    contextUsage,
    error,
    photoCaptureRequest,
    sendVideoFrame,
    start,
    status,
    stop,
    tasks: tasks.filter((task) => task.chatId === sessionId),
    toolActivities,
  };
}

function taskFromMessage(message: TaskPayload, fallbackChatId: string): VoiceTask {
  return {
    id: message.task_id || "",
    chatId: message.chat_id || fallbackChatId,
    instruction: message.instruction || "Sherpa task",
    kind: message.kind || "worker",
    parentId: message.parent_id || undefined,
    status: message.status || "running",
    phase: message.phase || "starting",
    progress: message.progress ?? 0,
    currentStep: message.current_step || "Starting",
    result: message.summary || undefined,
    previewTarget: message.preview_target,
    interactionMode: message.interaction_mode,
    updates: (message.updates || []).map((update) => ({
      phase: update.phase,
      progress: update.progress,
      message: update.message,
      nextStep: update.next_step || "",
      createdAt: update.created_at,
    })),
  };
}
