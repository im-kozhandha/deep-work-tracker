import { formatPercent, formatSeconds } from "../utils/format";

function Metric({ label, value, hint }) {
  return (
    <div className="metric" title={hint}>
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}

export default function SummaryCards({ summary }) {
  const averageFocused =
    summary.average_focused_seconds_completed === null
      ? null
      : Math.round(summary.average_focused_seconds_completed);

  return (
    <section className="summary-grid" aria-label="Productivity summary">
      <Metric label="Total sessions" value={summary.total_sessions} />
      <Metric label="Completed" value={summary.completed_count} hint="Finished within 110% of the scheduled time." />
      <Metric
        label="Completion rate"
        value={formatPercent(summary.completion_rate)}
        hint="Completed ÷ finished sessions (completed, overdue, interrupted, abandoned)."
      />
      <Metric
        label="Focused time"
        value={formatSeconds(summary.total_focused_seconds)}
        hint="Elapsed time minus paused time, across all started sessions."
      />
      <Metric
        label="Avg focused (completed)"
        value={formatSeconds(averageFocused)}
        hint="Mean focused time over completed sessions only."
      />
      <Metric label="Interruptions" value={summary.total_interruptions} hint="Total pause events." />
    </section>
  );
}