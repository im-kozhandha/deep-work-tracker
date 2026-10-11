const EMPTY_VALUE = "—";

function pad(value) {
  return String(value).padStart(2, "0");
}

export function formatDateTime(isoString) {
  if (!isoString) return EMPTY_VALUE;
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return EMPTY_VALUE;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatMinutes(totalMinutes) {
  if (totalMinutes === null || totalMinutes === undefined) return EMPTY_VALUE;
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours === 0) return `${minutes} min`;
  return minutes === 0 ? `${hours} h` : `${hours} h ${minutes} min`;
}

export function formatSeconds(totalSeconds) {
  if (totalSeconds === null || totalSeconds === undefined) return EMPTY_VALUE;
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) return `${hours}h ${pad(minutes)}m`;
  return `${minutes}m ${pad(seconds)}s`;
}

// Clock-style duration for countdowns: "MM:SS", or "H:MM:SS" from one hour up.
// Expects a non-negative number of seconds.
export function formatClock(totalSeconds) {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const seconds = safeSeconds % 60;
  if (hours > 0) return `${hours}:${pad(minutes)}:${pad(seconds)}`;
  return `${pad(minutes)}:${pad(seconds)}`;
}

export function formatPercent(value) {
  if (value === null || value === undefined) return EMPTY_VALUE;
  return `${value.toFixed(1)}%`;
}