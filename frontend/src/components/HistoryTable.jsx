import { formatDateTime, formatMinutes, formatSeconds } from "../utils/format";
import Countdown from "./Countdown";
import SessionControls from "./SessionControls";
import StatusBadge from "./StatusBadge";

function PauseCell({ session }) {
  if (session.pause_count === 0) return <span>0</span>;
  return (
    <details>
      <summary>{session.pause_count}</summary>
      <ul className="reason-list">
        {session.interruptions.map((interruption) => (
          <li key={interruption.id}>
            {interruption.reason}
            <span className="muted"> · {formatDateTime(interruption.pause_time)}</span>
          </li>
        ))}
      </ul>
    </details>
  );
}

export default function HistoryTable({
  sessions,
  fetchedAt,
  pendingIds,
  onStart,
  onPause,
  onResume,
  onComplete,
}) {
  if (sessions.length === 0) {
    return (
      <p className="empty-state">No sessions yet. Schedule your first session above.</p>
    );
  }

  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th scope="col">Session</th>
            <th scope="col">Status</th>
            <th scope="col">Scheduled</th>
            <th scope="col">Started</th>
            <th scope="col">Ended</th>
            <th scope="col">Pauses</th>
            <th scope="col" title="Wall-clock time from start to end (or to now), pauses included.">
              Elapsed
            </th>
            <th scope="col" title="Elapsed time minus paused time.">
              Focused
            </th>
            <th scope="col" title="Live countdown for running sessions.">
              Time left
            </th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((session) => (
            <tr key={session.id}>
              <td>
                <div className="cell-title">{session.title}</div>
                {session.goal && <div className="muted">{session.goal}</div>}
              </td>
              <td>
                <StatusBadge status={session.status} />
              </td>
              <td>{formatMinutes(session.scheduled_duration)}</td>
              <td>{formatDateTime(session.start_time)}</td>
              <td>{formatDateTime(session.end_time)}</td>
              <td>
                <PauseCell session={session} />
              </td>
              <td>{formatSeconds(session.elapsed_seconds)}</td>
              <td>{formatSeconds(session.focused_seconds)}</td>
              <td>
                <Countdown session={session} fetchedAt={fetchedAt} />
              </td>
              <td>
                <SessionControls
                  session={session}
                  busy={pendingIds.has(session.id)}
                  onStart={() => onStart(session)}
                  onPause={(reason) => onPause(session, reason)}
                  onResume={() => onResume(session)}
                  onComplete={() => onComplete(session)}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}