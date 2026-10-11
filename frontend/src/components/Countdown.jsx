import { useTick } from "../hooks/useTick";
import { formatClock } from "../utils/format";

// Backend rule: overdue when elapsed > scheduled x 110%. Seconds: minutes x 60 x 110 / 100.
const OVERDUE_LIMIT_SECONDS_PER_MINUTE = 66;
const SECONDS_PER_MINUTE = 60;
const MS_PER_SECOND = 1000;

/**
 * Live countdown for an active or paused session.
 *
 * Both figures start from server-computed seconds in the last history response and add the
 * client time since that response arrived (`fetchedAt`), so browser/server clock skew
 * never matters and every refresh re-anchors the display.
 */
export default function Countdown({ session, fetchedAt }) {
  const isActive = session.status === "active";
  const isPaused = session.status === "paused";
  const running = isActive || isPaused;
  const now = useTick(running);

  if (!running || session.elapsed_seconds === null || session.focused_seconds === null) {
    return <span className="muted">—</span>;
  }

  const secondsSinceFetch = Math.max(0, Math.floor((now - fetchedAt) / MS_PER_SECOND));
  const scheduledSeconds = session.scheduled_duration * SECONDS_PER_MINUTE;
  const overdueLimitSeconds = session.scheduled_duration * OVERDUE_LIMIT_SECONDS_PER_MINUTE;

  // Focused time only advances while active; paused sessions stay frozen.
  const focusedSeconds = session.focused_seconds + (isActive ? secondsSinceFetch : 0);
  // Wall-clock time (pauses included) always advances; this is what the overdue rule uses.
  const wallElapsedSeconds = session.elapsed_seconds + secondsSinceFetch;

  const remainingSeconds = scheduledSeconds - focusedSeconds;
  const secondsUntilOverdue = overdueLimitSeconds - wallElapsedSeconds;
  const isOver = remainingSeconds < 0;
  const isPastLimit = secondsUntilOverdue < 0;

  return (
    <div className="countdown">
      <div className={`countdown-main${isOver ? " countdown-over" : ""}`}>
        {isOver ? `+${formatClock(-remainingSeconds)} over` : `${formatClock(remainingSeconds)} left`}
        {isPaused && <span className="muted"> (paused)</span>}
      </div>
      <div
        className={`countdown-note${isPastLimit ? " countdown-over" : ""}`}
        title="Pauses count toward the 110% limit."
      >
        {isPastLimit
          ? "Past 110%: completing now = overdue"
          : `Overdue in ${formatClock(secondsUntilOverdue)}`}
      </div>
    </div>
  );
}