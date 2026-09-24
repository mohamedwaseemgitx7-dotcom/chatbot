import { useCallback, useEffect, useRef, useState } from "react";

const DEFAULT_SECONDS = 60;

/**
 * Server rate-limit cooldowns per feature ("chat", "image", "voice").
 * Started from a 429's Retry-After; the server still enforces the limit, this only keeps the UI honest.
 * @returns {{ remaining: (kind) => number, start: (kind, seconds?) => void }}
 */
export function useCooldown() {
  const until = useRef({});
  const [, setTick] = useState(0);
  const [active, setActive] = useState(false);

  const start = useCallback((kind, seconds) => {
    until.current[kind] = Date.now() + (seconds || DEFAULT_SECONDS) * 1000;
    setActive(true);
    setTick((n) => n + 1);
  }, []);

  const remaining = useCallback((kind) => Math.max(0, Math.ceil(((until.current[kind] || 0) - Date.now()) / 1000)), []);

  // Tick once a second while any cooldown runs, so countdowns update and controls re-enable on time.
  useEffect(() => {
    if (!active) return undefined;
    const id = setInterval(() => {
      setTick((n) => n + 1);
      if (Object.values(until.current).every((t) => t <= Date.now())) setActive(false);
    }, 1000);
    return () => clearInterval(id);
  }, [active]);

  return { remaining, start };
}
