import { useEffect, useState } from "react";
import { checkHealth } from "../services/botService";

/**
 * Network + backend reachability for the header status.
 * @returns {"checking" | "online" | "unreachable" | "offline" | "demo"}
 */
export function useConnection() {
  const [status, setStatus] = useState(() => (navigator.onLine === false ? "offline" : "checking"));

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      const result = await checkHealth();
      if (!cancelled) setStatus(result);
    };
    const onOffline = () => setStatus("offline");
    const onOnline = () => { setStatus("checking"); check(); };

    if (navigator.onLine !== false) check();
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      cancelled = true;
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  return status;
}
