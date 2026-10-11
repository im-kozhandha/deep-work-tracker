import { useEffect, useState } from "react";

const DEFAULT_TICK_MS = 1000;

// Returns the current time in ms, refreshed every `intervalMs` while `enabled`.
// The interval is cleared when disabled or unmounted, so idle rows cost nothing.
export function useTick(enabled, intervalMs = DEFAULT_TICK_MS) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!enabled) return undefined;
    setNow(Date.now());
    const intervalId = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(intervalId);
  }, [enabled, intervalMs]);

  return now;
}