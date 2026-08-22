import { useState, type FormEvent } from "react";
import { Eye, EyeOff } from "lucide-react";
import { authenticateAccount, createAccount, demoAccount } from "./accountApi";
import type { AuthenticatedSherpaAccount } from "./authTypes";
import "./AuthForm.css";

type Mode = "signin" | "create";

export function AuthForm({ onAuthenticated }: { onAuthenticated: (account: AuthenticatedSherpaAccount) => void }) {
  const [mode, setMode] = useState<Mode>("signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string>();
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(undefined);
    setSubmitting(true);
    try {
      if (mode === "create") await createAccount({ email, password, name });
      onAuthenticated(await authenticateAccount(email, password));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Authentication failed.");
    } finally {
      setSubmitting(false);
    }
  }

  function chooseMode(nextMode: Mode) {
    setMode(nextMode);
    setError(undefined);
  }

  function useDemoAccount() {
    setMode("signin");
    setEmail(demoAccount.email);
    setPassword(demoAccount.password);
    setName("");
    setError(undefined);
  }

  return (
    <main className="auth-page">
      <strong className="auth-brand">Sherpa</strong>
      <section className="auth-shell">
        <div className="auth-card">
          <h1 className="auth-title">{mode === "signin" ? "Sign in" : "Create account"}</h1>
          <div className="auth-modes" aria-label="Account access">
            <button aria-pressed={mode === "signin"} type="button" onClick={() => chooseMode("signin")}>Sign in</button>
            <button aria-pressed={mode === "create"} type="button" onClick={() => chooseMode("create")}>Create account</button>
          </div>
          <form id="sherpa-auth-form" onSubmit={submit}>
            <div className="auth-fields">
              {mode === "create" ? <label>Name<input autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} /></label> : null}
              <label>Email<input autoComplete="username" type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
              <label>Password<span className="auth-password"><input autoComplete={mode === "signin" ? "current-password" : "new-password"} type={showPassword ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} /><button aria-label={showPassword ? "Hide password" : "Show password"} type="button" onClick={() => setShowPassword((current) => !current)}>{showPassword ? <EyeOff /> : <Eye />}</button></span></label>
            </div>
            <div className="auth-secondary">
              {error ? <p className="auth-error" role="alert">{error}</p> : mode === "signin" ? <button className="auth-demo" type="button" onClick={useDemoAccount}>Use demo account</button> : null}
            </div>
          </form>
        </div>
        <button className="auth-submit" disabled={!email || !password || (mode === "create" && !name) || submitting} form="sherpa-auth-form" type="submit">{submitting ? "Working" : mode === "signin" ? "Sign in" : "Create account"}</button>
      </section>
    </main>
  );
}
