import { useState } from "react";
import type { PermissionSection } from "../connections/connectionTypes";
import { WorkspacePermissions } from "./WorkspacePermissions";
import { WorkspaceProfile } from "./WorkspaceProfile";
import "./PluginsView.css";
import "./WorkspaceView.css";

interface WorkspaceViewProps {
  accountId: string;
  error?: string;
  section?: PermissionSection;
  onError: (message: string) => void;
  onPermissionChange: (permissionId: string, enabled: boolean) => void;
}

export function WorkspaceView({ accountId, error, section, onError, onPermissionChange }: WorkspaceViewProps) {
  const account = section?.permissions.find((permission) => permission.connection === "google_workspace");
  const connected = account?.enabled ?? false;
  const [showEmail, setShowEmail] = useState(
    () => window.localStorage.getItem(`sherpa-workspace-show-email:${accountId}`) !== "false",
  );

  const changeEmailVisibility = (visible: boolean) => {
    window.localStorage.setItem(`sherpa-workspace-show-email:${accountId}`, String(visible));
    setShowEmail(visible);
  };

  return (
    <>
      <h1 className="plugins-view__title">Workspace</h1>
      <section className="plugins-view workspace-view" aria-label="Google Workspace">
        {error ? <p className="plugins-view__error" role="alert">{error}</p> : null}
        {account ? (
          <WorkspaceProfile
            account={account}
            showEmail={showEmail}
            onEmailVisibilityChange={changeEmailVisibility}
            onError={onError}
          />
        ) : null}
        <WorkspacePermissions
          connected={connected}
          permissions={section?.permissions.filter((permission) => !permission.connection) ?? []}
          onPermissionChange={onPermissionChange}
        />
      </section>
    </>
  );
}
