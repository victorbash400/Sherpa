import { useCallback, useEffect, useRef, useState } from "react";
import { AudioControls } from "./components/AudioControls";
import { ChatShell } from "./components/ChatShell";
import { ChatHistoryButton } from "./components/ChatHistoryButton";
import { ChatHistoryDrawer } from "./components/ChatHistoryDrawer";
import { ControlRail } from "./components/ControlRail";
import { FloatingVoiceOrb } from "./components/FloatingVoiceOrb";
import { MemoryView } from "./components/MemoryView";
import { useSherpaChat } from "./hooks/useSherpaChat";
import { useVoiceSession } from "./hooks/useVoiceSession";
import { useVoicePreview } from "./hooks/useVoicePreview";
import { Orb } from "./components/Orb";
import { RefreshButton } from "./components/RefreshButton";
import { TasksView } from "./components/TasksView";
import { VoiceSessionButton } from "./components/VoiceSessionButton";
import { VoicePicker } from "./components/VoicePicker";
import { VoiceTranscript } from "./components/VoiceTranscript";
import { VoiceToolActivity } from "./components/VoiceToolActivity";
import { loadVoice, saveVoice, type VoiceOption } from "./voice/voiceOptions";
import "./App.css";

export function App() {
  const [view, setView] = useState<"voice" | "chat" | "voices" | "tasks" | "memory">("voice");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [selectedVoice, setSelectedVoice] = useState(loadVoice);
  const [microphoneMuted, setMicrophoneMuted] = useState(false);
  const [speakerMuted, setSpeakerMuted] = useState(false);
  const [volume, setVolume] = useState(70);
  const [transcriptExpanded, setTranscriptExpanded] = useState(false);
  const automaticTaskViewRef = useRef(false);
  const hadActiveTasksRef = useRef(false);
  const chat = useSherpaChat();
  const appendVoiceTranscript = useCallback((role: "user" | "assistant", text: string) => {
    chat.appendTranscript(chat.activeChatId, role, text);
  }, [chat.activeChatId, chat.appendTranscript]);
  const voice = useVoiceSession({
    microphoneMuted,
    onTranscript: appendVoiceTranscript,
    sessionId: chat.activeChatId,
    speakerMuted,
    volume,
    voiceName: selectedVoice.id,
  });
  const voicePreview = useVoicePreview(volume, speakerMuted);
  const orbMode = voice.status === "speaking" ? "speaking" : voice.status === "listening" ? "listening" : "idle";
  const voiceActive = voice.status === "connecting" || voice.status === "listening" || voice.status === "speaking";
  const hasActiveTasks = voice.tasks.some((task) => task.status === "running");
  const hasTranscript = chat.activeChat.transcript.some((entry) => entry.text.trim().length > 0);

  useEffect(() => {
    if (!hasTranscript && transcriptExpanded) setTranscriptExpanded(false);
  }, [hasTranscript, transcriptExpanded]);

  useEffect(() => {
    const tasksBecameActive = hasActiveTasks && !hadActiveTasksRef.current;
    hadActiveTasksRef.current = hasActiveTasks;
    if (tasksBecameActive && voiceActive && view === "voice") {
      automaticTaskViewRef.current = true;
      setView("tasks");
      return;
    }
    if ((!hasActiveTasks || !voiceActive) && view === "tasks" && automaticTaskViewRef.current) {
      automaticTaskViewRef.current = false;
      setView("voice");
    }
  }, [hasActiveTasks, view, voiceActive]);

  const selectVoice = (nextVoice: VoiceOption) => {
    voice.stop();
    voicePreview.stop();
    setSelectedVoice(nextVoice);
    saveVoice(nextVoice);
  };

  const startNewChat = () => {
    voice.stop();
    chat.newChat();
    setHistoryOpen(false);
    setView("voice");
  };

  return (
    <main className="shell">
      <ControlRail
        activeView={view}
        computerActive={voice.computerActive}
        onOpenMemory={() => setView("memory")}
        onOpenTasks={() => {
          automaticTaskViewRef.current = false;
          setView("tasks");
        }}
        onOpenVoices={() => {
          voice.stop();
          setView("voices");
        }}
        onOpenSettings={() => undefined}
      />
      {view === "voice" ? (
        <>
          {hasTranscript ? (
            <VoiceTranscript entries={chat.activeChat.transcript} expanded={transcriptExpanded} onExpandedChange={setTranscriptExpanded} />
          ) : null}
          <section className="orb-stage" data-transcript-expanded={hasTranscript && transcriptExpanded} aria-label="Sherpa is listening">
            <Orb
              mode={orbMode}
              audioLevel={voice.audioLevel}
              hue={selectedVoice.hue}
            />
            <VoiceSessionButton hue={selectedVoice.hue} onStart={() => void voice.start()} onStop={voice.stop} status={voice.status} />
            <VoiceToolActivity activities={voice.toolActivities} />
          </section>
          {voice.error ? <p className="voice-error" role="alert">{voice.error}</p> : null}
          <AudioControls
            microphoneMuted={microphoneMuted}
            speakerMuted={speakerMuted}
            volume={volume}
            onMicrophoneMutedChange={setMicrophoneMuted}
            onSpeakerMutedChange={setSpeakerMuted}
            onVolumeChange={setVolume}
          />
        </>
      ) : view === "chat" ? (
        <ChatShell
          error={chat.error}
          messages={chat.activeChat.messages}
          onSend={(content) => void chat.send(content)}
          streaming={chat.streaming}
        />
      ) : view === "voices" ? (
        <VoicePicker
          error={voicePreview.error}
          onBack={() => {
            voicePreview.stop();
            setView("voice");
          }}
          onPreview={() => void voicePreview.preview(selectedVoice.id)}
          onSelect={selectVoice}
          previewing={voicePreview.playing}
          selected={selectedVoice}
        />
      ) : view === "tasks" ? (
        <>
          <TasksView tasks={voice.tasks} />
          {hasActiveTasks && voiceActive ? (
            <FloatingVoiceOrb
              audioLevel={voice.audioLevel}
              hue={selectedVoice.hue}
              mode={orbMode}
            />
          ) : null}
        </>
      ) : (
        <MemoryView />
      )}
      <ChatHistoryButton onClick={() => setHistoryOpen(true)} />
      <RefreshButton />
      <ChatHistoryDrawer
        activeChatId={chat.activeChatId}
        chats={chat.chats}
        disabled={chat.streaming}
        onClose={() => setHistoryOpen(false)}
        onDelete={chat.deleteChat}
        onNewChat={startNewChat}
        onSelect={(id) => {
          voice.stop();
          chat.selectChat(id);
          setHistoryOpen(false);
          setView("chat");
        }}
        open={historyOpen}
      />
    </main>
  );
}
