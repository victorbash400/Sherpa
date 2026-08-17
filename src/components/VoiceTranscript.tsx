import { useEffect, useRef, type CSSProperties } from "react";
import type { VoiceTranscriptEntry } from "../chat/chatTypes";
import "./TranscriptGlass.css";
import "./VoiceTranscript.css";

interface VoiceTranscriptProps {
  entries: VoiceTranscriptEntry[];
  expanded: boolean;
  hue: number;
  onExpandedChange: (expanded: boolean) => void;
}

export function VoiceTranscript({ entries, expanded, hue, onExpandedChange }: VoiceTranscriptProps) {
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const content = contentRef.current;
    if (content) content.scrollTo({ top: content.scrollHeight });
  }, [entries]);

  return (
    <section
      className="voice-transcript transcript-glass"
      data-expanded={expanded}
      aria-label="Live transcript"
      style={{ "--transcript-hue": hue } as CSSProperties}
    >
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
        <span aria-hidden="true" />
      </button>
    </section>
  );
}
