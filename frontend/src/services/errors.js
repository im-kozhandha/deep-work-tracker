import axios from "axios";

const NETWORK_MESSAGE =
  "Cannot reach the server. Make sure the backend is running and try again.";
const TIMEOUT_MESSAGE = "The server took too long to respond. Please try again.";
const SERVER_MESSAGE = "The server ran into a problem. Please try again in a moment.";
const UNKNOWN_MESSAGE = "Something unexpected went wrong.";

export class ApiError extends Error {
  constructor(message, { kind, status = null, fieldErrors = {} }) {
    super(message);
    this.name = "ApiError";
    this.kind = kind; // network | timeout | not_found | conflict | validation | server | http | unknown
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

function detailString(data) {
  return typeof data?.detail === "string" ? data.detail : null;
}

// FastAPI 422 bodies: detail = [{ loc: ["body", "title"], msg: "..." }, ...]
function extractFieldErrors(detail) {
  const fieldErrors = {};
  if (!Array.isArray(detail)) return fieldErrors;
  for (const item of detail) {
    const location = Array.isArray(item?.loc) ? item.loc : [];
    const field = location.length > 0 ? String(location[location.length - 1]) : "request";
    if (!(field in fieldErrors)) fieldErrors[field] = item?.msg || "Invalid value.";
  }
  return fieldErrors;
}

function describeFieldErrors(fieldErrors) {
  const parts = Object.entries(fieldErrors).map(([field, message]) => `${field}: ${message}`);
  return parts.length > 0 ? `Invalid input — ${parts.join("; ")}` : "The request was invalid.";
}

export function toApiError(error) {
  if (error instanceof ApiError) return error;
  if (!axios.isAxiosError(error)) {
    return new ApiError(UNKNOWN_MESSAGE, { kind: "unknown" });
  }

  if (!error.response) {
    const timedOut = error.code === "ECONNABORTED" || error.code === "ETIMEDOUT";
    return new ApiError(timedOut ? TIMEOUT_MESSAGE : NETWORK_MESSAGE, {
      kind: timedOut ? "timeout" : "network",
    });
  }

  const { status, data } = error.response;
  const detail = detailString(data);

  if (status === 404) {
    return new ApiError(detail ?? "The requested session was not found.", {
      kind: "not_found",
      status,
    });
  }
  if (status === 409) {
    return new ApiError(detail ?? "That action is not allowed in the session's current state.", {
      kind: "conflict",
      status,
    });
  }
  if (status === 422) {
    const fieldErrors = extractFieldErrors(data?.detail);
    return new ApiError(describeFieldErrors(fieldErrors), {
      kind: "validation",
      status,
      fieldErrors,
    });
  }
  if (status >= 500) {
    return new ApiError(SERVER_MESSAGE, { kind: "server", status });
  }
  return new ApiError(detail ?? `Request failed (HTTP ${status}).`, { kind: "http", status });
}