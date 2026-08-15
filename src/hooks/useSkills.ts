import { useEffect, useState } from "react";

export type SherpaSkill = {
  id: string;
  name: string;
  description: string;
  instructions: string;
  built_in: boolean;
};

export function useSkills(active: boolean) {
  const [skills, setSkills] = useState<SherpaSkill[]>([]);
  const [error, setError] = useState<string>();

  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    void fetch("http://127.0.0.1:8000/skills", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Could not load Sherpa skills.");
        return response.json() as Promise<{ skills: SherpaSkill[] }>;
      })
      .then((result) => {
        setSkills(result.skills);
        setError(undefined);
      })
      .catch((reason: unknown) => {
        if (!(reason instanceof DOMException && reason.name === "AbortError")) {
          setError(reason instanceof Error ? reason.message : "Could not load Sherpa skills.");
        }
      });
    return () => controller.abort();
  }, [active]);

  async function updateSkill(id: string, instructions: string) {
    const response = await fetch(`http://127.0.0.1:8000/skills/${encodeURIComponent(id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ instructions }),
    });
    if (!response.ok) {
      const result = await response.json().catch(() => null) as { detail?: string } | null;
      throw new Error(result?.detail || "Could not save this skill.");
    }
    const updated = await response.json() as SherpaSkill;
    setSkills((current) => current.map((skill) => skill.id === id ? updated : skill));
  }

  return { error, skills, updateSkill };
}
