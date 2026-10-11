import { useState } from "react";

import { FORM_LIMITS } from "../constants";

const INITIAL_VALUES = { title: "", goal: "", duration: "25" };

function validate({ title, goal, duration }) {
  const errors = {};
  const trimmedTitle = title.trim();
  if (!trimmedTitle) {
    errors.title = "Title is required.";
  } else if (trimmedTitle.length > FORM_LIMITS.titleMax) {
    errors.title = `Title must be at most ${FORM_LIMITS.titleMax} characters.`;
  }

  const durationValue = Number(duration);
  if (duration.trim() === "") {
    errors.duration = "Duration is required.";
  } else if (
    !Number.isInteger(durationValue) ||
    durationValue < FORM_LIMITS.durationMin ||
    durationValue > FORM_LIMITS.durationMax
  ) {
    errors.duration = `Enter a whole number of minutes from ${FORM_LIMITS.durationMin} to ${FORM_LIMITS.durationMax}.`;
  }

  if (goal.trim().length > FORM_LIMITS.goalMax) {
    errors.goal = `Goal must be at most ${FORM_LIMITS.goalMax} characters.`;
  }
  return errors;
}

export default function SessionForm({ onCreate }) {
  const [values, setValues] = useState(INITIAL_VALUES);
  const [fieldErrors, setFieldErrors] = useState({});
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;
    setValues((previous) => ({ ...previous, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setResult(null);
    const clientErrors = validate(values);
    setFieldErrors(clientErrors);
    if (Object.keys(clientErrors).length > 0) return;

    setSubmitting(true);
    try {
      const session = await onCreate({
        title: values.title.trim(),
        goal: values.goal.trim(),
        duration: Number(values.duration),
      });
      setResult({
        type: "success",
        text: `Scheduled “${session.title}” for ${session.scheduled_duration} minutes.`,
      });
      setValues((previous) => ({ ...previous, title: "", goal: "" }));
    } catch (error) {
      setFieldErrors(error.fieldErrors ?? {});
      setResult({ type: "error", text: error.message });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="card" aria-labelledby="schedule-heading">
      <h2 id="schedule-heading">Schedule a session</h2>
      <form className="session-form" onSubmit={handleSubmit} noValidate>
        <div className="field">
          <label htmlFor="title">Title *</label>
          <input
            id="title"
            name="title"
            type="text"
            value={values.title}
            onChange={handleChange}
            maxLength={FORM_LIMITS.titleMax + 50}
            aria-invalid={Boolean(fieldErrors.title)}
            aria-describedby={fieldErrors.title ? "title-error" : undefined}
            disabled={submitting}
          />
          {fieldErrors.title && (
            <p id="title-error" className="field-error">
              {fieldErrors.title}
            </p>
          )}
        </div>

        <div className="field">
          <label htmlFor="goal">Goal</label>
          <input
            id="goal"
            name="goal"
            type="text"
            value={values.goal}
            onChange={handleChange}
            aria-invalid={Boolean(fieldErrors.goal)}
            aria-describedby={fieldErrors.goal ? "goal-error" : undefined}
            disabled={submitting}
          />
          {fieldErrors.goal && (
            <p id="goal-error" className="field-error">
              {fieldErrors.goal}
            </p>
          )}
        </div>

        <div className="field field-narrow">
          <label htmlFor="duration">Duration (minutes) *</label>
          <input
            id="duration"
            name="duration"
            type="number"
            inputMode="numeric"
            min={FORM_LIMITS.durationMin}
            max={FORM_LIMITS.durationMax}
            step="1"
            value={values.duration}
            onChange={handleChange}
            aria-invalid={Boolean(fieldErrors.duration)}
            aria-describedby={fieldErrors.duration ? "duration-error" : undefined}
            disabled={submitting}
          />
          {fieldErrors.duration && (
            <p id="duration-error" className="field-error">
              {fieldErrors.duration}
            </p>
          )}
        </div>

        <button type="submit" className="button button-primary" disabled={submitting}>
          {submitting ? "Scheduling…" : "Schedule"}
        </button>
      </form>

      {result && (
        <p
          className={`form-message form-message-${result.type}`}
          role={result.type === "error" ? "alert" : "status"}
        >
          {result.text}
        </p>
      )}
    </section>
  );
}