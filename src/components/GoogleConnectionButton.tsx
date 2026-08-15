interface GoogleConnectionButtonProps {
  connection: string;
  connected: boolean;
  onError: (message: string) => void;
}

export function GoogleConnectionButton({ connection, connected, onError }: GoogleConnectionButtonProps) {
  const updateConnection = async () => {
    onError("");
    try {
      const connectionName = connection.replace("google_", "");
      if (connected) {
        const response = await fetch(`http://127.0.0.1:8000/oauth/google/${connectionName}`, {
          method: "DELETE",
        });
        if (!response.ok) throw new Error("Sherpa could not disconnect that account.");
        return;
      }

      const response = await fetch(`http://127.0.0.1:8000/oauth/google/${connectionName}/start`, {
        method: "POST",
      });
      const payload = await response.json() as { authorization_url?: string; detail?: string };
      if (!response.ok || !payload.authorization_url) {
        throw new Error(payload.detail || "Sherpa could not start Google sign-in.");
      }
      if (!window.sherpaSystem) {
        throw new Error("Restart Sherpa to enable Google sign-in.");
      }
      const opened = await window.sherpaSystem.openExternal(payload.authorization_url);
      if (!opened) throw new Error("Sherpa could not open Google sign-in.");
    } catch (reason) {
      onError(reason instanceof Error ? reason.message : "Sherpa could not update that connection.");
    }
  };

  return (
    <button className="workspace-profile__button" type="button" onClick={() => void updateConnection()}>
      {connected ? "Disconnect" : "Connect"}
    </button>
  );
}
