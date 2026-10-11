import { useEffect, useState } from "react";

import { FORM_LIMITS, TERMINAL_STATUSES } from "../constants";

export default function SessionControls({ session, busy, onStart, onPause, onResume, onComplete }) {
  const [isPausing, setIsPausing] = useState(false);
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState(null);

  function closePauseForm() {
    setIsPausing(false);
    setReason("");
    setReasonError(null);
  }

  // If the server moves the session out of "active", the pause form no longer applies.
  useEffect(() => {
    if (session.status !== "active") {
      setIsPausing(false);
      setReason("");
      setReasonError(null);
    }
  }, [session.status]);

  async function handlePauseSubmit(event) {
    event.preventDefault();
    const trimmedReason = reason.trim();
    if (!trimmedReason) {
      setReasonError("Enter a reason for pausing.");
      return;
    }
    const succeeded = await onPause(trimmedReason);
    if (succeeded) closePauseForm();
  }

  if (TERMINAL_STATUSES.includes(session.status)) {
    return <span className="muted">No actions</span>;
  }

  if (session.status === "scheduled") {
    return (
      <button type="button" className="button" disabled={busy} onClick={onStart}>
        Start
      </button>
    );
  }

  if (session.status === "paused") {
    return (
      <button type="button" className="button" disabled={busy} onClick={onResume}>
        Resume
      </button>
    );
  }

  if (session.status === "active") {
    if (isPausing) {
      return (
        <form className="pause-form" onSubmit={handlePauseSubmit} noValidate>
          <label className="visually-hidden" htmlFor={`pause-reason-${session.id}`}>
            Reason for pausing
          </label>
          <input
            id={`pause-reason-${session.id}`}
            type="text"
            placeholder="Reason for pausing"
            value={reason}
            maxLength={FORM_LIMITS.reasonMax}
            onChange={(event) => setReason(event.target.value)}
            aria-invalid={Boolean(reasonError)}
            disabled={busy}
            autoFocus
          />
          {reasonError && <p className="field-error">{reasonError}</p>}
          <div className="button-row">
            <button type="submit" className="button button-primary" disabled={busy}>
              Confirm pause
            </button>
            <button type="button" className="button" disabled={busy} onClick={closePauseForm}>
              Cancel
            </button>
          </div>
        </form>
      );
    }
    return (
      <div className="button-row">
        <button type="button" className="button" disabled={busy} onClick={() => setIsPausing(true)}>
          Pause
        </button>
        <button type="button" className="button button-primary" disabled={busy} onClick={onComplete}>
          Complete
        </button>
      </div>
    );
  }

  return null;
}