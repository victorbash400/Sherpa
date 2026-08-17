import { CalendarDays, Cloud, ContactRound, FileQuestion, FileText, HardDrive, ListChecks, Mail, Presentation, Sheet, SquareTerminal, Video } from "lucide-react";
import type { Permission } from "../connections/connectionTypes";

interface WorkspacePermissionsProps {
  connected: boolean;
  permissions: Permission[];
  onPermissionChange: (permissionId: string, enabled: boolean) => void;
}

const icons = {
  "workspace.drive": HardDrive,
  "workspace.docs": FileText,
  "workspace.sheets": Sheet,
  "workspace.slides": Presentation,
  "workspace.gmail": Mail,
  "workspace.calendar": CalendarDays,
  "workspace.people": ContactRound,
  "workspace.tasks": ListChecks,
  "workspace.forms": FileQuestion,
  "workspace.meet": Video,
  "cloud.resources": Cloud,
  "cloud.cli": SquareTerminal,
};

export function WorkspacePermissions({ connected, permissions, onPermissionChange }: WorkspacePermissionsProps) {
  return (
    <section className={`workspace-permissions${connected ? "" : " workspace-permissions--disabled"}`}>
      <h2>Allowed access</h2>
      <div className="permission-section__rows">
        {permissions.map((permission) => {
          const Icon = icons[permission.id as keyof typeof icons] ?? FileText;
          return (
            <div className="permission-row" key={permission.id}>
              <Icon aria-hidden="true" />
              <span>
                <strong>{permission.name}</strong>
                <small>{permission.description}</small>
              </span>
              <label className="permission-switch">
                <input
                  type="checkbox"
                  checked={permission.enabled}
                  disabled={!connected}
                  onChange={(event) => onPermissionChange(permission.id, event.target.checked)}
                  aria-label={`${permission.enabled ? "Disable" : "Enable"} ${permission.name}`}
                />
                <span aria-hidden="true" />
              </label>
            </div>
          );
        })}
      </div>
    </section>
  );
}
