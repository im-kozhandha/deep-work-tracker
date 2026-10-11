import { STATUS_LABELS, TERMINAL_STATUSES } from "../constants";

export const CHART_WINDOW_DAYS = 14;

const SECONDS_PER_MINUTE = 60;
const PERCENT = 100;

function roundToOneDecimal(value) {
  return Math.round(value * 10) / 10;
}

// Local calendar date as "YYYY-MM-DD" (the user's own day boundaries).
export function localDateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

// The last `days` local days, oldest first, ending today.
export function buildDayWindow(days = CHART_WINDOW_DAYS, today = new Date()) {
  const dayWindow = [];
  for (let offset = days - 1; offset >= 0; offset -= 1) {
    const day = new Date(today.getFullYear(), today.getMonth(), today.getDate() - offset);
    dayWindow.push({
      key: localDateKey(day),
      label: day.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    });
  }
  return dayWindow;
}

// Focused minutes per day, attributed to the local day the session STARTED.
export function focusedMinutesByDay(sessions, dayWindow) {
  const secondsByDay = new Map(dayWindow.map((day) => [day.key, 0]));
  const sessionsByDay = new Map(dayWindow.map((day) => [day.key, 0]));

  for (const session of sessions) {
    if (!session.start_time || session.focused_seconds === null) continue;
    const key = localDateKey(new Date(session.start_time));
    if (!secondsByDay.has(key)) continue;
    secondsByDay.set(key, secondsByDay.get(key) + session.focused_seconds);
    sessionsByDay.set(key, sessionsByDay.get(key) + 1);
  }

  return dayWindow.map((day) => ({
    label: day.label,
    minutes: roundToOneDecimal(secondsByDay.get(day.key) / SECONDS_PER_MINUTE),
    sessions: sessionsByDay.get(day.key),
  }));
}

// Completion rate per day over sessions that FINISHED (terminal status) that local day.
// Days with no finished session get rate = null so the line shows a gap, not 0%.
export function completionTrendByDay(sessions, dayWindow) {
  const finishedByDay = new Map(dayWindow.map((day) => [day.key, 0]));
  const completedByDay = new Map(dayWindow.map((day) => [day.key, 0]));

  for (const session of sessions) {
    if (!session.end_time || !TERMINAL_STATUSES.includes(session.status)) continue;
    const key = localDateKey(new Date(session.end_time));
    if (!finishedByDay.has(key)) continue;
    finishedByDay.set(key, finishedByDay.get(key) + 1);
    if (session.status === "completed") {
      completedByDay.set(key, completedByDay.get(key) + 1);
    }
  }

  return dayWindow.map((day) => {
    const finished = finishedByDay.get(day.key);
    const completed = completedByDay.get(day.key);
    return {
      label: day.label,
      finished,
      completed,
      rate: finished > 0 ? roundToOneDecimal((completed / finished) * PERCENT) : null,
    };
  });
}

// Donut data from the backend's status_counts; statuses with zero sessions are hidden.
export function statusChartData(statusCounts) {
  return Object.entries(STATUS_LABELS)
    .map(([status, name]) => ({ status, name, value: statusCounts?.[status] ?? 0 }))
    .filter((entry) => entry.value > 0);
}