import { useEffect, useState } from "react";
import { MemoryItems } from "./MemoryItems";
import { MemoryPersonalization } from "./MemoryPersonalization";
import { MemorySettings } from "./MemorySettings";
import type { MemorySnapshot, MemorySettingsValues } from "./memoryTypes";
import "./MemoryView.css";

const memoryUrl = "http://127.0.0.1:8000/memory";

export function MemoryView() {
  const [snapshot, setSnapshot] = useState<MemorySnapshot>();
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    void requestMemory({ signal: controller.signal }).then(setSnapshot).catch((reason: unknown) => {
      if (!(reason instanceof DOMException && reason.name === "AbortError")) setError(messageFrom(reason));
    });
    return () => controller.abort();
  }, []);

  const updateSettings = async (values: Partial<MemorySettingsValues>) => {
    setSaving(true);
    setError(undefined);
    try {
      setSnapshot(await requestMemory({
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values),
      }, "/settings"));
    } catch (reason) {
      setError(messageFrom(reason));
    } finally {
      setSaving(false);
    }
  };

  const updateItem = async (id: string, values: { content?: string; active?: boolean }) => {
    setError(undefined);
    try {
      setSnapshot(await requestMemory({
        method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values),
      }, `/items/${encodeURIComponent(id)}`));
    } catch (reason) {
      setError(messageFrom(reason));
    }
  };

  const deleteAll = async () => {
    if (!window.confirm("Delete every learned Sherpa memory? Personalization settings will remain.")) return;
    try {
      setSnapshot(await requestMemory({ method: "DELETE" }));
    } catch (reason) {
      setError(messageFrom(reason));
    }
  };

  return (
    <>
      <h1 className="memory-view__title">Memory</h1>
      <section className="memory-view" aria-label="Sherpa memory">
      {error ? <p className="memory-view__error" role="alert">{error}</p> : null}
      {snapshot ? <>
        <MemoryPersonalization limits={snapshot.limits} saving={saving} settings={snapshot.settings} onSave={updateSettings} />
        <MemorySettings settings={snapshot.settings} onChange={updateSettings} onDelete={deleteAll} />
        <MemoryItems memories={snapshot.memories} onChange={updateItem} />
      </> : null}
      </section>
    </>
  );
}

async function requestMemory(init?: RequestInit, path = "") {
  const response = await fetch(`${memoryUrl}${path}`, init);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Sherpa memory request failed." })) as { detail?: string };
    throw new Error(payload.detail || "Sherpa memory request failed.");
  }
  return response.json() as Promise<MemorySnapshot>;
}

function messageFrom(reason: unknown) {
  return reason instanceof Error ? reason.message : "Sherpa memory request failed.";
}
