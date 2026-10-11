// Mirrors the backend's SessionStatus values. The backend remains the source of truth.
export const STATUS_LABELS = {
  scheduled: "Scheduled",
  active: "Active",
  paused: "Paused",
  completed: "Completed",
  interrupted: "Interrupted",
  abandoned: "Abandoned",
  overdue: "Overdue",
};

export const STATUS_HINTS = {
  scheduled: "Created but not started yet.",
  active: "Currently running.",
  paused: "Paused; resume it before the abandonment timeout.",
  completed: "Finished within 110% of the scheduled duration.",
  interrupted: "Paused more than three times.",
  abandoned: "Paused and never resumed in time.",
  overdue: "Finished after 110% of the scheduled duration.",
};

// Statuses after which the backend rejects every lifecycle action.
export const TERMINAL_STATUSES = ["completed", "interrupted", "abandoned", "overdue"];

// Client-side limits for fast feedback only; the backend validates independently.
export const FORM_LIMITS = {
  titleMax: 200,
  goalMax: 1000,
  reasonMax: 500,
  durationMin: 1,
  durationMax: 1440,
};