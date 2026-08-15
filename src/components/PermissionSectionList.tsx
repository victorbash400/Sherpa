import { AppWindow, Cloud, MousePointer2, PanelsTopLeft } from "lucide-react";
import type { PermissionSection } from "../connections/connectionTypes";
import { GoogleConnectionSwitch } from "./GoogleConnectionSwitch";

interface PermissionSectionListProps {
  sections: PermissionSection[];
  onConnectionError: (message: string) => void;
  onPermissionChange: (permissionId: string, enabled: boolean) => void;
}

export function PermissionSectionList({ sections, onConnectionError, onPermissionChange }: PermissionSectionListProps) {
  return sections.map((section) => (
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
            {permission.connection ? (
              <GoogleConnectionSwitch connection={permission.connection} connected={permission.enabled} onError={onConnectionError} />
            ) : (
              <label className="permission-switch">
                <input
                  type="checkbox"
                  checked={permission.enabled}
                  onChange={(event) => onPermissionChange(permission.id, event.target.checked)}
                  aria-label={`${permission.enabled ? "Disable" : "Enable"} ${permission.name}`}
                />
                <span aria-hidden="true" />
              </label>
            )}
          </div>
        ))}
      </div>
    </section>
  ));
}

function PermissionIcon({ permissionId }: { permissionId: string }) {
  if (permissionId === "connection.google_workspace" || permissionId.startsWith("workspace.")) {
    return <img src="/gnome-panel-workspace-switcher-svgrepo-com.svg" alt="" aria-hidden="true" />;
  }
  if (permissionId === "connection.google_cloud" || permissionId.startsWith("cloud.")) return <Cloud aria-hidden="true" />;
  if (permissionId === "browser.read") return <img src="/browser-svgrepo-com.svg" alt="" aria-hidden="true" />;
  if (permissionId === "browser.interact") return <img src="/chrome-svgrepo-com (1).svg" alt="" aria-hidden="true" />;
  if (permissionId === "browser.tabs") return <PanelsTopLeft aria-hidden="true" />;
  if (permissionId === "mac.screen") return <img src="/computer-svgrepo-com.svg" alt="" aria-hidden="true" />;
  if (permissionId === "mac.control") return <MousePointer2 aria-hidden="true" />;
  if (permissionId === "google.models") return <Cloud aria-hidden="true" />;
  return <AppWindow aria-hidden="true" />;
}
