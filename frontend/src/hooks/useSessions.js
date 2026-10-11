import { useCallback, useEffect, useRef, useState } from "react";

import * as api from "../services/api";

const POLL_INTERVAL_MS = 15000;

function quoted(session) {
  return `“${session.title}”`;
}

function describeStart(session) {
  return { type: "success", text: `Started ${quoted(session)}.` };
}

function describePause(session) {
  if (session.status === "interrupted") {
    return {
      type: "warning",
      text: `${quoted(session)} was interrupted: it has now been paused more than three times and can no longer be changed.`,
    };
  }
  return {
    type: "info",
    text: `Paused ${quoted(session)}. Resume it soon; an unresumed pause is eventually marked abandoned.`,
  };
}

function describeResume(session) {
  return { type: "success", text: `Resumed ${quoted(session)}.` };
}

function describeComplete(session) {
  if (session.status === "overdue") {
    return {
      type: "warning",
      text: `${quoted(session)} finished after 110% of its scheduled time, so it is marked overdue.`,
    };
  }
  return { type: "success", text: `Completed ${quoted(session)}.` };
}

export function useSessions() {
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [pendingIds, setPendingIds] = useState(() => new Set());
  const latestRequestId = useRef(0);

  // Never throws. Responses that arrive out of order are ignored.
  const refresh = useCallback(async () => {
    const requestId = ++latestRequestId.current;
    try {
      const data = await api.getHistory();
      if (requestId !== latestRequestId.current) return;
      setHistory(data);
      setLoadError(null);
    } catch (error) {
      if (requestId !== latestRequestId.current) return;
      setLoadError(error.message);
    } finally {
      if (requestId === latestRequestId.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const intervalId = setInterval(() => {
      if (!document.hidden) refresh();
    }, POLL_INTERVAL_MS);
    return () => clearInterval(intervalId);
  }, [refresh]);

  const createSession = useCallback(
    async (payload) => {
      const session = await api.scheduleSession(payload);
      await refresh();
      return session;
    },
    [refresh]
  );

  // Runs one lifecycle call, reports the outcome, then re-syncs from the server.
  // Resolves to true on success and false on failure; never throws.
  const runSessionAction = useCallback(
    async (session, call, describeSuccess) => {
      setPendingIds((previous) => new Set(previous).add(session.id));
      try {
        const updated = await call();
        setNotice(describeSuccess(updated));
        return true;
      } catch (error) {
        setNotice({ type: "error", text: error.message });
        return false;
      } finally {
        await refresh();
        setPendingIds((previous) => {
          const next = new Set(previous);
          next.delete(session.id);
          return next;
        });
      }
    },
    [refresh]
  );

  const start = useCallback(
    (session) => runSessionAction(session, () => api.startSession(session.id), describeStart),
    [runSessionAction]
  );
  const pause = useCallback(
    (session, reason) =>
      runSessionAction(session, () => api.pauseSession(session.id, reason), describePause),
    [runSessionAction]
  );
  const resume = useCallback(
    (session) => runSessionAction(session, () => api.resumeSession(session.id), describeResume),
    [runSessionAction]
  );
  const complete = useCallback(
    (session) => runSessionAction(session, () => api.completeSession(session.id), describeComplete),
    [runSessionAction]
  );

  const dismissNotice = useCallback(() => setNotice(null), []);

  return {
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
  };
}