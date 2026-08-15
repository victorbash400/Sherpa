import type { VoiceTaskUpdate } from "../hooks/useVoiceSession";
import { Markdown } from "./Markdown";
import "./TaskUpdateList.css";

export function TaskUpdateList({ updates }: { updates: VoiceTaskUpdate[] }) {
  return (
    <ol className="task-updates" aria-label="Task updates">
      {updates.map((update) => (
        <li key={`${update.createdAt}-${update.message}`}>
          <div>
            <Markdown content={update.message} />
            {update.nextStep ? (
              <div className="task-updates__next">
                <Markdown content={update.nextStep} />
              </div>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  );
}
