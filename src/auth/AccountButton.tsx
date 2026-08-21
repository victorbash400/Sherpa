import { LogOut, UserRound } from "lucide-react";
import { useState } from "react";
import { logoutAccount } from "./accountApi";
import type { AuthenticatedSherpaAccount } from "./authTypes";
import "./AccountButton.css";

export function AccountButton({ account, onSignedOut }: { account: AuthenticatedSherpaAccount; onSignedOut: () => void }) {
  const [error, setError] = useState<string>();
  const [signingOut, setSigningOut] = useState(false);

  async function signOut() {
    setError(undefined);
    setSigningOut(true);
    try {
      await logoutAccount(account.token);
      onSignedOut();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not sign out.");
      setSigningOut(false);
    }
  }

  return (
    <details className="account-button">
      <summary aria-label={`Open account menu for ${account.name}`} title={account.name}><UserRound /></summary>
      <section>
        <p><span>Signed in as</span><strong>{account.name}</strong><small>{account.email}</small></p>
        {error ? <p role="alert">{error}</p> : null}
        <button disabled={signingOut} type="button" onClick={() => void signOut()}><LogOut />{signingOut ? "Signing out" : "Sign out"}</button>
      </section>
    </details>
  );
}
