import { useEffect, useRef, useState } from "react";
import { DEMO_NOTICE } from "./DemoNotice";
import { LogoMark } from "./Icons";
import { login } from "../services/authService";
import { ApiError } from "../services/http";
import "./LoginPage.css";

function loginError(error) {
  if (!(error instanceof ApiError)) return { text: "Couldn't log in. Please try again." };
  if (error.kind === "offline") return { text: "You're offline. Check your internet connection and try again." };
  if (error.kind === "network" || error.kind === "timeout") return { text: "Can't reach the FarmerAssist server. Please try again in a moment." };
  if (error.status === 401) return { text: "Incorrect username or password." };
  if (error.status === 429) return { text: "Too many login attempts.", wait: error.retryAfter || 60 };
  if (error.status === 503) return { text: "Login isn't configured on the server yet. Please contact the administrator." };
  return { text: "Couldn't log in. Please try again." };
}

export default function LoginPage({ onLogin, notice }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [waitUntil, setWaitUntil] = useState(0);
  const [, tick] = useState(0);
  const userRef = useRef(null);

  useEffect(() => { userRef.current?.focus(); }, []);
  const secondsLeft = Math.max(0, Math.ceil((waitUntil - Date.now()) / 1000));
  useEffect(() => {
    if (!secondsLeft) return undefined;
    const id = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, [secondsLeft]);

  async function submit(event) {
    event.preventDefault();
    if (busy || secondsLeft || !username.trim() || !password) return;
    setBusy(true);
    setError(null);
    try {
      onLogin(await login(username.trim(), password));
    } catch (err) {
      const info = loginError(err);
      setError(info.text);
      if (info.wait) setWaitUntil(Date.now() + info.wait * 1000);
      setPassword("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login">
      <form className="login__card" onSubmit={submit} aria-labelledby="login-title" noValidate>
        <div className="login__brand">
          <LogoMark size={44} />
          <div>
            <h1 id="login-title" className="login__title">FarmerAssist</h1>
            <p className="login__subtitle">Agriculture AI Assistant</p>
          </div>
        </div>

        {notice && !error && <p className="login__notice" role="status">{notice}</p>}
        {error && (
          <p className="login__error" role="alert">
            {error}{secondsLeft > 0 && ` Try again in ${secondsLeft} seconds.`}
          </p>
        )}

        <label className="login__field">
          <span>Username</span>
          <input ref={userRef} value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username"
                 autoCapitalize="none" spellCheck="false" maxLength={64} required />
        </label>
        <label className="login__field">
          <span>Password</span>
          <span className="login__password">
            <input type={showPassword ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)}
                   autoComplete="current-password" maxLength={256} required />
            <button type="button" className="login__toggle" onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword}>
              {showPassword ? "Hide" : "Show"}
            </button>
          </span>
        </label>

        <button type="submit" className="btn btn--primary login__submit" disabled={busy || secondsLeft > 0 || !username.trim() || !password}>
          {busy && <span className="spinner" aria-hidden="true" />}
          {busy ? "Logging in…" : secondsLeft > 0 ? `Try again in ${secondsLeft} s` : "Login"}
        </button>

        <p className="login__about">{DEMO_NOTICE}</p>
      </form>
    </main>
  );
}
