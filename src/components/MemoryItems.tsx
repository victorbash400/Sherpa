import { useState } from "react";
import type { MemoryItem } from "./memoryTypes";
import "./MemoryItems.css";

export function MemoryItems({ memories, onChange }: { memories: MemoryItem[]; onChange: (id: string, values: { content?: string; active?: boolean }) => Promise<void> }) {
  return (
    <section className="memory-items">
      <h2>Remembered</h2>
      <p>Details Sherpa retained from your conversations and completed work.</p>
      {memories.length ? <div className="memory-items__rows">{memories.map((memory) => <MemoryRow key={memory.id} memory={memory} onChange={onChange} />)}</div> : null}
    </section>
  );
}

function MemoryRow({ memory, onChange }: { memory: MemoryItem; onChange: (id: string, values: { content?: string; active?: boolean }) => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [content, setContent] = useState(memory.content);
  return (
    <article className="memory-item-row" data-active={memory.active}>
      <span className="memory-item-row__content">
        <small>{memory.category}{memory.editable ? "" : " · Managed"}</small>
        {editing ? <textarea maxLength={320} value={content} onChange={(event) => setContent(event.target.value)} /> : <strong>{memory.content}</strong>}
      </span>
      <span className="memory-item-row__actions">
        {memory.editable ? <button type="button" onClick={() => { if (editing) void onChange(memory.id, { content }); setEditing(!editing); }}>{editing ? "Save" : "Edit"}</button> : null}
        <label className="memory-toggle" aria-label={`${memory.active ? "Disable" : "Enable"} memory`}><input type="checkbox" checked={memory.active} onChange={(event) => void onChange(memory.id, { active: event.target.checked })} /><i aria-hidden="true" /></label>
      </span>
    </article>
  );
}
