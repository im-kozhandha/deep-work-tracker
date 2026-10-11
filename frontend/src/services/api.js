import axios from "axios";

import { toApiError } from "./errors";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 10000;

const client = axios.create({
  baseURL: BASE_URL,
  timeout: REQUEST_TIMEOUT_MS,
  headers: { "Content-Type": "application/json" },
});

// Every failed request rejects with an ApiError carrying a user-friendly message.
client.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(toApiError(error))
);

export async function scheduleSession({ title, duration, goal }) {
  const payload = { title, duration };
  if (goal) payload.goal = goal;
  const { data } = await client.post("/sessions/", payload);
  return data;
}

export async function startSession(sessionId) {
  const { data } = await client.patch(`/sessions/${sessionId}/start`);
  return data;
}

export async function pauseSession(sessionId, reason) {
  const { data } = await client.patch(`/sessions/${sessionId}/pause`, { reason });
  return data;
}

export async function resumeSession(sessionId) {
  const { data } = await client.patch(`/sessions/${sessionId}/resume`);
  return data;
}

export async function completeSession(sessionId) {
  const { data } = await client.patch(`/sessions/${sessionId}/complete`);
  return data;
}

export async function getHistory() {
  const { data } = await client.get("/sessions/history");
  return data;
}