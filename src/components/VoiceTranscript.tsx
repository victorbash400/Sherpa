import { Maximize2, Minimize2 } from "lucide-react";
import { useEffect, useRef } from "react";
import type { VoiceTranscriptEntry } from "../chat/chatTypes";
import "./VoiceTranscript.css";

interface VoiceTranscriptProps {
  entries: VoiceTranscriptEntry[];
  expanded: boolean;
  onExpandedChange: (expanded: boolean) => void;
}

export function VoiceTranscript({ entries, expanded, onExpandedChange }: VoiceTranscriptProps) {
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const content = contentRef.current;
    if (content) content.scrollTo({ top: content.scrollHeight });
  }, [entries]);

  return (
    <section className="voice-transcript" data-expanded={expanded} aria-label="Live transcript">
      <div className="voice-transcript__content" ref={contentRef}>
        {entries.map((entry) => (
          <p data-role={entry.role} key={entry.id}>{entry.text}</p>
        ))}
      </div>
      <button
        aria-label={expanded ? "Collapse transcript" : "Expand transcript"}
        onClick={() => onExpandedChange(!expanded)}
        type="button"
      >
        {expanded ? <Minimize2 aria-hidden="true" /> : <Maximize2 aria-hidden="true" />}
      </button>
    </section>
  );
}
