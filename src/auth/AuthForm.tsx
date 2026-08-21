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

  function switchMode() {
    setMode((current) => current === "signin" ? "create" : "signin");
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
      <section className="auth-card">
        <div className="auth-mark" aria-hidden="true"><span /></div>
        <h1>{mode === "signin" ? "Sign in to Sherpa" : "Create your Sherpa account"}</h1>
        <p>{mode === "signin" ? "Continue with your private workspace." : "Start with a fresh private workspace."}</p>
        <form onSubmit={submit}>
          {mode === "create" ? <label>Name<input autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} /></label> : null}
          <label>Email<input autoComplete="username" type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label>Password<span className="auth-password"><input autoComplete={mode === "signin" ? "current-password" : "new-password"} type={showPassword ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} /><button aria-label={showPassword ? "Hide password" : "Show password"} type="button" onClick={() => setShowPassword((current) => !current)}>{showPassword ? <EyeOff /> : <Eye />}</button></span></label>
          {error ? <p className="auth-error" role="alert">{error}</p> : null}
          <button disabled={!email || !password || (mode === "create" && !name) || submitting} type="submit">{submitting ? "Working" : mode === "signin" ? "Sign in" : "Create account"}</button>
        </form>
        <p className="auth-switch">{mode === "signin" ? "New to Sherpa?" : "Already have an account?"}<button type="button" onClick={switchMode}>{mode === "signin" ? "Create account" : "Sign in"}</button></p>
        {mode === "signin" ? <button className="auth-demo" type="button" onClick={useDemoAccount}>Use demo account</button> : null}
      </section>
    </main>
  );
}
