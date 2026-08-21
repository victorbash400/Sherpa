import type { AuthenticatedSherpaAccount, SherpaAccount } from "./authTypes";

const apiUrl = "http://127.0.0.1:8000/accounts";
const sessionKey = "sherpa-account-session";
export const demoAccount = { email: "demo@sherpa.local", password: "sherpa-demo" };

export async function resumeAccount(): Promise<AuthenticatedSherpaAccount | null> {
  const token = window.localStorage.getItem(sessionKey);
  if (!token) return null;
  const response = await fetch(`${apiUrl}/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  if (response.status === 401) {
    window.localStorage.removeItem(sessionKey);
    return null;
  }
  const account = await responseJson<SherpaAccount>(response);
  return { ...account, token };
}

export async function createAccount(values: { email: string; password: string; name: string }): Promise<void> {
  const response = await fetch(apiUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(values),
  });
  await responseJson<SherpaAccount>(response);
}

export async function authenticateAccount(email: string, password: string): Promise<AuthenticatedSherpaAccount> {
  const response = await fetch(`${apiUrl}/authenticate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const account = await responseJson<AuthenticatedSherpaAccount>(response);
  window.localStorage.setItem(sessionKey, account.token);
  return account;
}

export async function logoutAccount(token: string): Promise<void> {
  const response = await fetch(`${apiUrl}/logout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  await responseJson<{ signed_out: boolean }>(response);
  window.localStorage.removeItem(sessionKey);
}

async function responseJson<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => ({ detail: "Sherpa account request failed." })) as T & { detail?: string };
  if (!response.ok) throw new Error(body.detail || "Sherpa account request failed.");
  return body;
}
