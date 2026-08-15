import { useEffect, useState } from "react";
import { AppWindow, Cloud, MousePointer2, PanelsTopLeft } from "lucide-react";
import "./PluginsView.css";

interface Permission {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
}

interface PermissionSection {
  id: string;
  title: string;
  permissions: Permission[];
}

export function PluginsView() {
  const [sections, setSections] = useState<PermissionSection[]>([]);
  const [error, setError] = useState<string>();

  useEffect(() => {
    const controller = new AbortController();
    void fetch("http://127.0.0.1:8000/connections", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Could not read Sherpa permissions.");
        return response.json() as Promise<{ sections: PermissionSection[] }>;
      })
      .then((payload) => setSections(payload.sections))
      .catch((reason: unknown) => {
        if (!(reason instanceof DOMException && reason.name === "AbortError")) {
          setError(reason instanceof Error ? reason.message : "Could not read Sherpa permissions.");
        }
      });
    return () => controller.abort();
  }, []);

  const setPermission = async (permissionId: string, enabled: boolean) => {
    setError(undefined);
    const previous = sections;
    setSections((current) => updatePermission(current, permissionId, enabled));
    try {
      const response = await fetch(`http://127.0.0.1:8000/permissions/${encodeURIComponent(permissionId)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
      if (!response.ok) throw new Error("Sherpa could not update that permission.");
    } catch (reason) {
      setSections(previous);
      setError(reason instanceof Error ? reason.message : "Sherpa could not update that permission.");
    }
  };

  return (
    <>
      <h1 className="plugins-view__title">Plugins</h1>
      <section className="plugins-view" aria-label="Sherpa plugins">
      {error ? <p className="plugins-view__error" role="alert">{error}</p> : null}
      {sections.map((section) => (
        <section className="permission-section" key={section.id}>
          <h2>{section.title}</h2>
          <div className="permission-section__rows">
            {section.permissions.map((permission) => (
              <div className="permission-row" key={permission.id}>
                <PermissionIcon permissionId={permission.id} />
                <span>
                  <strong>{permission.name}</strong>
                  <small>{permission.description}</small>
                </span>
                <label className="permission-switch">
                  <input
                    type="checkbox"
                    checked={permission.enabled}
                    onChange={(event) => void setPermission(permission.id, event.target.checked)}
                    aria-label={`${permission.enabled ? "Disable" : "Enable"} ${permission.name}`}
                  />
                  <span aria-hidden="true" />
                </label>
              </div>
            ))}
          </div>
        </section>
      ))}
      </section>
    </>
  );
}

function PermissionIcon({ permissionId }: { permissionId: string }) {
  if (permissionId === "browser.read") return <img src="/browser-svgrepo-com.svg" alt="" aria-hidden="true" />;
  if (permissionId === "browser.interact") return <img src="/chrome-svgrepo-com (1).svg" alt="" aria-hidden="true" />;
  if (permissionId === "browser.tabs") return <PanelsTopLeft aria-hidden="true" />;
  if (permissionId === "mac.screen") return <img src="/computer-svgrepo-com.svg" alt="" aria-hidden="true" />;
  if (permissionId === "mac.control") return <MousePointer2 aria-hidden="true" />;
  if (permissionId === "google.models") return <Cloud aria-hidden="true" />;
  return <AppWindow aria-hidden="true" />;
}

function updatePermission(sections: PermissionSection[], permissionId: string, enabled: boolean) {
  return sections.map((section) => ({
    ...section,
    permissions: section.permissions.map((permission) =>
      permission.id === permissionId ? { ...permission, enabled } : permission
    ),
  }));
}
