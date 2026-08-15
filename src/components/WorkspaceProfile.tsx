import { useState } from "react";
import { CircleUserRound } from "lucide-react";
import type { Permission } from "../connections/connectionTypes";
import { GoogleConnectionButton } from "./GoogleConnectionButton";

interface WorkspaceProfileProps {
  account: Permission;
  onError: (message: string) => void;
}

export function WorkspaceProfile({ account, onError }: WorkspaceProfileProps) {
  const profile = account.profile;
  const [photoFailed, setPhotoFailed] = useState(false);
  const showPhoto = account.enabled && profile?.picture && !photoFailed;

  return (
    <section className="workspace-profile" aria-label="Google account">
      <div className="workspace-profile__avatar">
        {showPhoto ? (
          <img src={profile.picture} alt="" onError={() => setPhotoFailed(true)} />
        ) : (
          <CircleUserRound aria-hidden="true" />
        )}
      </div>
      <div className="workspace-profile__identity">
        <strong>{account.enabled ? profile?.name || "Google account" : "Google Workspace"}</strong>
        <span>{account.enabled ? profile?.email : "Connect your Google account to Sherpa"}</span>
      </div>
      <GoogleConnectionButton
        connection={account.connection ?? "google_workspace"}
        connected={account.enabled}
        onError={onError}
      />
    </section>
  );
}
