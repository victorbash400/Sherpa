import { useEffect, useState } from "react";
import { App } from "../App";
import { resumeAccount } from "./accountApi";
import { AuthForm } from "./AuthForm";
import type { AuthenticatedSherpaAccount } from "./authTypes";

export function AuthGate() {
  const [account, setAccount] = useState<AuthenticatedSherpaAccount | null>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    void resumeAccount().then(setAccount).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : "Sherpa could not restore your account.");
      setAccount(null);
    });
  }, []);

  if (account === undefined) return <main className="auth-page" aria-label="Opening Sherpa" />;
  if (!account) return <>{error ? <p role="alert">{error}</p> : null}<AuthForm onAuthenticated={setAccount} /></>;
  return <App account={account} onSignedOut={() => setAccount(null)} />;
}
