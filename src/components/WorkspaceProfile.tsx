import { useState } from "react";
import { CircleUserRound, Eye, EyeOff } from "lucide-react";
import type { Permission } from "../connections/connectionTypes";
import { GoogleConnectionButton } from "./GoogleConnectionButton";

interface WorkspaceProfileProps {
  account: Permission;
  showEmail: boolean;
  onEmailVisibilityChange: (visible: boolean) => void;
  onError: (message: string) => void;
}

export function WorkspaceProfile({ account, showEmail, onEmailVisibilityChange, onError }: WorkspaceProfileProps) {
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
        {account.enabled ? (
          <span className="workspace-profile__email">
            {showEmail ? profile?.email : "Email hidden"}
            <button
              type="button"
              onClick={() => onEmailVisibilityChange(!showEmail)}
              aria-label={showEmail ? "Hide email address" : "Show email address"}
            >
              {showEmail ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
            </button>
          </span>
        ) : (
          <span>Connect your Google account to Sherpa</span>
        )}
      </div>
      <GoogleConnectionButton
        connection={account.connection ?? "google_workspace"}
        connected={account.enabled}
        onError={onError}
      />
    </section>
  );
}
