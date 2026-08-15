import { useCallback, useEffect, useState } from "react";
import type { PermissionSection } from "../connections/connectionTypes";

export function useConnectionSections() {
  const [sections, setSections] = useState<PermissionSection[]>([]);
  const [error, setError] = useState<string>();

  const load = useCallback((signal?: AbortSignal) => {
    return fetch("http://127.0.0.1:8000/connections", { signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Could not read Sherpa permissions.");
        return response.json() as Promise<{ sections: PermissionSection[] }>;
      })
      .then((payload) => setSections(payload.sections));
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal).catch((reason: unknown) => {
      if (!(reason instanceof DOMException && reason.name === "AbortError")) {
        setError(reason instanceof Error ? reason.message : "Could not read Sherpa permissions.");
      }
    });
    return () => controller.abort();
  }, [load]);

  useEffect(() => {
    const events = new EventSource("http://127.0.0.1:8000/connections/events");
    events.addEventListener("message", () => void load());
    return () => events.close();
  }, [load]);

  const setPermission = async (permissionId: string, enabled: boolean) => {
    setError(undefined);
    const previous = sections;
    setSections((current) => updatePermission(current, permissionId, enabled));
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/permissions/${encodeURIComponent(permissionId)}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ enabled }),
        },
      );
      if (!response.ok) throw new Error("Sherpa could not update that permission.");
    } catch (reason) {
      setSections(previous);
      setError(reason instanceof Error ? reason.message : "Sherpa could not update that permission.");
    }
  };

  return { error, sections, setError, setPermission };
}

function updatePermission(sections: PermissionSection[], permissionId: string, enabled: boolean) {
  return sections.map((section) => ({
    ...section,
    permissions: section.permissions.map((permission) =>
      permission.id === permissionId ? { ...permission, enabled } : permission
    ),
  }));
}
