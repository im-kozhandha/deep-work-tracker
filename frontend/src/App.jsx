import { useMemo } from "react";

import HistoryTable from "./components/HistoryTable";
import Notice from "./components/Notice";
import ProductivityCharts from "./components/ProductivityCharts";
import SessionForm from "./components/SessionForm";
import SummaryCards from "./components/SummaryCards";
import { useSessions } from "./hooks/useSessions";

export default function App() {
  const {
    history,
    loading,
    loadError,
    notice,
    dismissNotice,
    pendingIds,
    refresh,
    createSession,
    start,
    pause,
    resume,
    complete,
  } = useSessions();

  const sessions = history?.sessions ?? [];

  // Client time at which the current history snapshot arrived. Countdowns add the seconds
  // elapsed since this moment to the server-computed values, so clock skew cannot affect them.
  const fetchedAt = useMemo(() => Date.now(), [history]);

  return (
    <main className="container">
      <header className="page-header">
        <h1>Deep Work Session Tracker</h1>
        <p className="muted">Schedule focused sessions, track interruptions, review your history.</p>
      </header>

      <Notice notice={notice} onDismiss={dismissNotice} />

      <SessionForm onCreate={createSession} />

      {history && <SummaryCards summary={history.summary} />}

      <section className="card" aria-labelledby="history-heading">
        <div className="section-header">
          <h2 id="history-heading">Session history</h2>
          <button type="button" className="button" onClick={refresh}>
            Refresh
          </button>
        </div>

        {loadError && (
          <div className="notice notice-error" role="alert">
            <span>
              {history
                ? `Could not refresh: ${loadError} Showing the last loaded data.`
                : loadError}
            </span>
            <button type="button" className="button" onClick={refresh}>
              Retry
            </button>
          </div>
        )}

        {loading && !history ? (
          <p className="muted">Loading sessions…</p>
        ) : (
          history && (
            <HistoryTable
              sessions={sessions}
              fetchedAt={fetchedAt}
              pendingIds={pendingIds}
              onStart={start}
              onPause={pause}
              onResume={resume}
              onComplete={complete}
            />
          )
        )}
      </section>

      {history && <ProductivityCharts sessions={sessions} summary={history.summary} />}
    </main>
  );
}