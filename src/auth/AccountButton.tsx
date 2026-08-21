import { LogOut, UserRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { logoutAccount } from "./accountApi";
import type { AuthenticatedSherpaAccount } from "./authTypes";
import "./AccountButton.css";

export function AccountButton({ account, onSignedOut }: { account: AuthenticatedSherpaAccount; onSignedOut: () => void }) {
  const [error, setError] = useState<string>();
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function closeOnOutsidePress(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("pointerdown", closeOnOutsidePress);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsidePress);
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
    <div className="account-button" ref={rootRef}>
      <button className="account-button__trigger" aria-expanded={open} aria-haspopup="menu" aria-label={`Open account menu for ${account.name}`} title={account.name} type="button" onClick={() => setOpen((current) => !current)}><UserRound /></button>
      {open ? <section aria-label="Account menu">
        <p><span>Signed in as</span><strong>{account.name}</strong><small>{account.email}</small></p>
        {error ? <p role="alert">{error}</p> : null}
        <button disabled={signingOut} type="button" onClick={() => void signOut()}><LogOut />{signingOut ? "Signing out" : "Sign out"}</button>
      </section> : null}
    </div>
  );
}
