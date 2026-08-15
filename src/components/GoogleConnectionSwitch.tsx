interface GoogleConnectionSwitchProps {
  connection: string;
  connected: boolean;
  onError: (message: string) => void;
}

export function GoogleConnectionSwitch({
  connection,
  connected,
  onError,
}: GoogleConnectionSwitchProps) {
  const updateConnection = async () => {
    onError("");
    try {
      if (connected) {
        const response = await fetch(
          `http://127.0.0.1:8000/oauth/google/${connection.replace("google_", "")}`,
          { method: "DELETE" },
        );
        if (!response.ok) throw new Error("Sherpa could not disconnect that account.");
        return;
      }
      const response = await fetch(
        `http://127.0.0.1:8000/oauth/google/${connection.replace("google_", "")}/start`,
        { method: "POST" },
      );
      const payload = await response.json() as { authorization_url?: string; detail?: string };
      if (!response.ok || !payload.authorization_url) {
        throw new Error(payload.detail || "Sherpa could not start Google sign-in.");
      }
      const opened = await window.sherpaSystem?.openExternal(payload.authorization_url);
      if (!opened) throw new Error("Sherpa could not open Google sign-in.");
    } catch (reason) {
      onError(reason instanceof Error ? reason.message : "Sherpa could not update that connection.");
    }
  };

  return (
    <label className="permission-switch">
      <input
        type="checkbox"
        checked={connected}
        onChange={() => void updateConnection()}
        aria-label={`${connected ? "Disconnect" : "Connect"} Google account`}
      />
      <span aria-hidden="true" />
    </label>
  );
}
