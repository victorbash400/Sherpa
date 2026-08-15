import { Search, SquarePen, Trash2 } from "lucide-react";
import { useState } from "react";
import type { SherpaChat } from "../chat/chatTypes";
import "./ChatHistoryDrawer.css";

interface ChatHistoryDrawerProps {
  activeChatId: string;
  chats: SherpaChat[];
  disabled: boolean;
  onClose: () => void;
  onDelete: (id: string) => void;
  onNewChat: () => void;
  onSelect: (id: string) => void;
  open: boolean;
}

export function ChatHistoryDrawer({ activeChatId, chats, disabled, onClose, onDelete, onNewChat, onSelect, open }: ChatHistoryDrawerProps) {
  const [searching, setSearching] = useState(false);
  const [query, setQuery] = useState("");
  const normalizedQuery = query.trim().toLowerCase();
  const matches = chats.filter((chat) => chat.title.toLowerCase().includes(normalizedQuery));

  return (
    <>
      <button className="chat-history-backdrop" data-open={open} disabled={!open} aria-label="Close chat history" onClick={onClose} type="button" />
      <aside className="chat-history-drawer" data-open={open} aria-hidden={!open} aria-label="Chat history" inert={!open}>
        <nav>
          <button onClick={onNewChat} type="button"><SquarePen aria-hidden="true" />New chat</button>
          <button aria-expanded={searching} onClick={() => setSearching((current) => !current)} type="button"><Search aria-hidden="true" />Search chats</button>
          {searching ? <label><Search aria-hidden="true" /><input autoFocus={open} onChange={(event) => setQuery(event.target.value)} placeholder="Search chats" value={query} /></label> : null}
          <section className="chat-history-list" aria-label="Past chats">
            {matches.map((chat) => (
              <article key={chat.id}>
                <button className="chat-history-item" aria-current={chat.id === activeChatId ? "page" : undefined} onClick={() => onSelect(chat.id)} type="button"><span>{chat.title}</span></button>
                <button className="chat-history-delete" aria-label={`Delete ${chat.title}`} disabled={disabled} onClick={() => onDelete(chat.id)} title="Delete chat" type="button"><Trash2 aria-hidden="true" /></button>
              </article>
            ))}
            {!matches.length ? <p>No chats found.</p> : null}
          </section>
        </nav>
      </aside>
    </>
  );
}
