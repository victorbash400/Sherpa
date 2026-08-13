import { useState } from "react";
import { AudioControls } from "./components/AudioControls";
import { ChatShell } from "./components/ChatShell";
import { ChatHistoryButton } from "./components/ChatHistoryButton";
import { ChatHistoryDrawer } from "./components/ChatHistoryDrawer";
import { ControlRail } from "./components/ControlRail";
import { useSherpaChat } from "./hooks/useSherpaChat";
import { Orb } from "./components/Orb";
import "./App.css";

export function App() {
  const [view, setView] = useState<"voice" | "chat">("voice");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [microphoneMuted, setMicrophoneMuted] = useState(false);
  const [speakerMuted, setSpeakerMuted] = useState(false);
  const [volume, setVolume] = useState(70);
  const chat = useSherpaChat();

  const startNewChat = () => {
    chat.newChat();
    setHistoryOpen(false);
    setView("voice");
  };

  return (
    <main className="shell">
      <ControlRail
        activeView={view}
        onToggleChat={() => setView((current) => current === "voice" ? "chat" : "voice")}
        onOpenSettings={() => undefined}
      />
      {view === "voice" ? (
        <>
          <section className="orb-stage" aria-label="Sherpa is listening">
            <Orb mode="listening" audioLevel={0} />
          </section>
          <AudioControls
            microphoneMuted={microphoneMuted}
            speakerMuted={speakerMuted}
            volume={volume}
            onMicrophoneMutedChange={setMicrophoneMuted}
            onSpeakerMutedChange={setSpeakerMuted}
            onVolumeChange={setVolume}
          />
        </>
      ) : (
        <ChatShell
          error={chat.error}
          messages={chat.activeChat.messages}
          onSend={(content) => void chat.send(content)}
          streaming={chat.streaming}
        />
      )}
      <ChatHistoryButton onClick={() => setHistoryOpen(true)} />
      <ChatHistoryDrawer
        activeChatId={chat.activeChatId}
        chats={chat.chats}
        disabled={chat.streaming}
        onClose={() => setHistoryOpen(false)}
        onDelete={chat.deleteChat}
        onNewChat={startNewChat}
        onSelect={(id) => {
          chat.selectChat(id);
          setHistoryOpen(false);
          setView("chat");
        }}
        open={historyOpen}
      />
    </main>
  );
}
