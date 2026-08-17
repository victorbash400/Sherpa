import { useCallback, useEffect, useRef, useState } from "react";
import { AudioControls } from "./components/AudioControls";
import { CameraOrbPreview } from "./components/CameraOrbPreview";
import { AccessibilityView } from "./components/AccessibilityView";
import { ChatShell } from "./components/ChatShell";
import { ChatHistoryButton } from "./components/ChatHistoryButton";
import { ChatHistoryDrawer } from "./components/ChatHistoryDrawer";
import { ControlRail } from "./components/ControlRail";
import { FloatingVoiceOrb } from "./components/FloatingVoiceOrb";
import { MemoryView } from "./components/MemoryView";
import { PluginsView } from "./components/PluginsView";
import { PetsView } from "./components/PetsView";
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
import { WorkspaceView } from "./components/WorkspaceView";
import { SidebarToggle } from "./components/SidebarToggle";
import { SkillsView } from "./components/SkillsView";
import { useConnectionSections } from "./hooks/useConnectionSections";
import { useSkills } from "./hooks/useSkills";
import type { VoiceTranscriptEntry } from "./chat/chatTypes";
import {
  loadAccessibilitySettings,
  saveAccessibilitySettings,
  type AccessibilitySettings,
} from "./accessibility/accessibilitySettings";
import { loadVoice, saveVoice, type VoiceOption } from "./voice/voiceOptions";
import "./App.css";

export function App() {
  const [view, setView] = useState<"voice" | "chat" | "voices" | "tasks" | "memory" | "plugins" | "skills" | "workspace" | "accessibility" | "pets">("voice");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectedVoice, setSelectedVoice] = useState(loadVoice);
  const [microphoneMuted, setMicrophoneMuted] = useState(false);
  const [speakerMuted, setSpeakerMuted] = useState(false);
  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [cameraError, setCameraError] = useState<string>();
  const [volume, setVolume] = useState(70);
  const [transcriptExpanded, setTranscriptExpanded] = useState(false);
  const [windowFocused, setWindowFocused] = useState(true);
  const [accessibilitySettings, setAccessibilitySettings] = useState(loadAccessibilitySettings);
  const automaticTaskViewRef = useRef(false);
  const hadActiveTasksRef = useRef(false);
  const petTaskStatusesRef = useRef(new Map<string, string>());
  const chat = useSherpaChat();
  const connections = useConnectionSections();
  const skills = useSkills(view === "skills");
  const appendVoiceTranscript = useCallback((entry: VoiceTranscriptEntry) => {
    chat.updateTranscript(chat.activeChatId, entry);
  }, [chat.activeChatId, chat.updateTranscript]);
  const completeVoiceTurn = useCallback(() => {
    chat.completeVoiceTurn(chat.activeChatId);
  }, [chat.activeChatId, chat.completeVoiceTurn]);
  const voice = useVoiceSession({
    microphoneMuted,
    onTranscript: appendVoiceTranscript,
    onTurnComplete: completeVoiceTurn,
    sessionId: chat.activeChatId,
    speakerMuted,
    spokenLanguage: accessibilitySettings.spokenLanguage,
    volume,
    voiceName: selectedVoice.id,
  });
  const voicePreview = useVoicePreview(volume, speakerMuted);
  const orbMode = voice.status === "speaking" ? "speaking" : voice.status === "listening" ? "listening" : "idle";
  const voiceActive = voice.status === "connecting" || voice.status === "listening" || voice.status === "speaking";
  const hasActiveTasks = voice.tasks.some((task) => ["queued", "running", "blocked"].includes(task.status));
  const hasRunningTasks = voice.tasks.some((task) => task.status === "running");
  const hasTranscript = chat.activeChat.transcript.some((entry) => entry.text.trim().length > 0);

  useEffect(() => {
    return window.sherpaSystem?.onWindowFocusChanged(setWindowFocused);
  }, []);

  useEffect(() => {
    window.sherpaPet?.setWorking(hasRunningTasks);
  }, [hasRunningTasks]);

  useEffect(() => {
    const previous = petTaskStatusesRef.current;
    const completedCount = voice.tasks.filter((task) => (
      task.status === "completed"
      && previous.has(task.id)
      && previous.get(task.id) !== "completed"
    )).length;
    petTaskStatusesRef.current = new Map(voice.tasks.map((task) => [task.id, task.status]));
    if (completedCount) window.sherpaPet?.celebrate(completedCount);
  }, [voice.tasks]);

  useEffect(() => {
    window.sherpaPet?.setTranscript({
      entries: chat.activeChat.transcript.slice(-3).map(({ id, role, text }) => ({ id, role, text })),
      hue: selectedVoice.hue,
      status: voice.status,
    });
  }, [chat.activeChat.transcript, selectedVoice.hue, voice.status]);

  useEffect(() => {
    return window.sherpaPet?.onVoiceToggle(() => {
      if (voiceActive) voice.stop();
      else void voice.start();
    });
  }, [voice.start, voice.stop, voiceActive]);

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

  const updateAccessibilitySettings = (settings: AccessibilitySettings) => {
    if (settings.spokenLanguage !== accessibilitySettings.spokenLanguage && voiceActive) {
      voice.stop();
    }
    setAccessibilitySettings(settings);
    saveAccessibilitySettings(settings);
  };

  return (
    <main className="shell" data-sidebar-open={sidebarOpen} data-window-focused={windowFocused}>
      <SidebarToggle open={sidebarOpen} onToggle={() => setSidebarOpen((current) => !current)} />
      <ControlRail
        activeView={view}
        computerActive={voice.computerActive}
        expanded={sidebarOpen}
        onOpenAccessibility={() => setView("accessibility")}
        onOpenMemory={() => setView("memory")}
        onOpenPets={() => setView("pets")}
        onOpenPlugins={() => setView("plugins")}
        onOpenSkills={() => setView("skills")}
        onOpenWorkspace={() => setView("workspace")}
        onOpenVoice={() => {
          voicePreview.stop();
          automaticTaskViewRef.current = false;
          setView("voice");
        }}
        onOpenTasks={() => {
          automaticTaskViewRef.current = false;
          setView("tasks");
        }}
        onOpenVoices={() => {
          voice.stop();
          setView("voices");
        }}
      />
      {view === "voice" ? (
        <>
          {hasTranscript ? (
            <VoiceTranscript entries={chat.activeChat.transcript} expanded={transcriptExpanded} hue={selectedVoice.hue} onExpandedChange={setTranscriptExpanded} />
          ) : null}
          <section className="orb-stage" data-transcript-expanded={hasTranscript && transcriptExpanded} aria-label="Sherpa is listening">
            <div className="voice-orb-visual" data-camera-active={cameraEnabled}>
              <CameraOrbPreview active={cameraEnabled} onError={setCameraError} onFrame={voice.sendVideoFrame} />
              <Orb
                mode={orbMode}
                audioLevel={voice.audioLevel}
                hue={selectedVoice.hue}
              />
            </div>
            <VoiceSessionButton hue={selectedVoice.hue} onStart={() => void voice.start()} onStop={voice.stop} status={voice.status} />
            <VoiceToolActivity activities={voice.toolActivities} context={voice.contextUsage} />
          </section>
          {voice.error || cameraError ? <p className="voice-error" role="alert">{cameraError || voice.error}</p> : null}
          <AudioControls
            cameraEnabled={cameraEnabled}
            microphoneMuted={microphoneMuted}
            speakerMuted={speakerMuted}
            volume={volume}
            onCameraEnabledChange={setCameraEnabled}
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
      ) : null}
      <div hidden={view !== "memory"}>
        <MemoryView active={view === "memory"} />
      </div>
      <div hidden={view !== "plugins"}>
        <PluginsView
          error={connections.error}
          sections={connections.sections}
          onError={(message) => connections.setError(message || undefined)}
          onPermissionChange={(id, enabled) => void connections.setPermission(id, enabled)}
        />
      </div>
      <div hidden={view !== "workspace"}>
        <WorkspaceView
          error={connections.error}
          section={connections.sections.find((section) => section.id === "workspace")}
          onError={(message) => connections.setError(message || undefined)}
          onPermissionChange={(id, enabled) => void connections.setPermission(id, enabled)}
        />
      </div>
      <div hidden={view !== "skills"}>
        <SkillsView error={skills.error} skills={skills.skills} onSave={skills.updateSkill} />
      </div>
      <div hidden={view !== "accessibility"}>
        <AccessibilityView
          onChange={updateAccessibilitySettings}
          settings={accessibilitySettings}
        />
      </div>
      <div hidden={view !== "pets"}>
        <PetsView active={view === "pets"} />
      </div>
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
          setView("voice");
        }}
        open={historyOpen}
      />
    </main>
  );
}
