import { useCallback, useEffect, useState } from "react";
import App from "./App";
import LoginPage from "./components/LoginPage";
import { logout, verifySession } from "./services/authService";
import { USE_BACKEND } from "./services/botService";
import { UNAUTHORIZED_EVENT, getSession } from "./services/session";

/**
 * Two routes: /login and / (the assistant, login required).
 * Demo mode (VITE_USE_BACKEND=false) has no server to log in to, so it opens the assistant directly.
 */
export default function Root() {
  const [path, setPath] = useState(window.location.pathname);
  const [session, setSession] = useState(getSession);
  const [notice, setNotice] = useState(null);

  const navigate = useCallback((to, { replace = false } = {}) => {
    if (window.location.pathname !== to) window.history[replace ? "replaceState" : "pushState"](null, "", to);
    setPath(to);
  }, []);

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    const onUnauthorized = () => {
      setSession(null);
      setNotice("Your session has ended. Please log in again.");
      navigate("/login", { replace: true });
    };
    window.addEventListener("popstate", onPop);
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => {
      window.removeEventListener("popstate", onPop);
      window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    };
  }, [navigate]);

  // A stored token may have been revoked or the server secret rotated: confirm it once on load.
  useEffect(() => {
    if (USE_BACKEND && getSession()) verifySession().catch(() => {});
  }, []);

  const needsLogin = USE_BACKEND && !session;
  useEffect(() => {
    if (!USE_BACKEND) return;
    if (needsLogin && path !== "/login") navigate("/login", { replace: true });
    if (!needsLogin && path === "/login") navigate("/", { replace: true });
  }, [needsLogin, path, navigate]);

  const onLogin = (next) => {
    setSession(next);
    setNotice(null);
    navigate("/", { replace: true });
  };

  const onLogout = async () => {
    await logout();
    setSession(null);
    setNotice("You have been logged out.");
    navigate("/login", { replace: true });
  };

  if (needsLogin || path === "/login") {
    return needsLogin ? <LoginPage onLogin={onLogin} notice={notice} /> : null;
  }
  return <App user={session?.username} onLogout={USE_BACKEND ? onLogout : null} />;
}
