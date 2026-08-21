import { LogOut, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import { logoutAccount } from "./accountApi";
import type { AuthenticatedSherpaAccount } from "./authTypes";
import "./AccountButton.css";

export function AccountButton({ account, onSignedOut }: { account: AuthenticatedSherpaAccount; onSignedOut: () => void }) {
  const [error, setError] = useState<string>();
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  useEffect(() => {
    if (!open) return;
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

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
    <>
      {open ? <div className="account-button__dismiss" aria-hidden="true" onClick={() => setOpen(false)} /> : null}
      <div className="account-button">
        <button className="account-button__trigger" aria-expanded={open} aria-haspopup="menu" aria-label={`Open account menu for ${account.name}`} title={account.name} type="button" onClick={() => setOpen((current) => !current)}><UserRound /></button>
        {open ? <section aria-label="Account menu">
          <p><span>Signed in as</span><strong>{account.name}</strong><small>{account.email}</small></p>
          {error ? <p role="alert">{error}</p> : null}
          <button disabled={signingOut} type="button" onClick={() => void signOut()}><LogOut />{signingOut ? "Signing out" : "Sign out"}</button>
        </section> : null}
      </div>
    </>
  );
}
