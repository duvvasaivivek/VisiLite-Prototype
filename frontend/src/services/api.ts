import type { PerfStats, PrivacyStats, TaskStatus } from "../types";

const API = "";

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export const api = {
  createTask: (instruction: string, start_url?: string) =>
    json<TaskStatus>("/api/tasks", {
      method: "POST",
      body: JSON.stringify({ instruction, start_url }),
    }),
  getTask: (id: string) => json<TaskStatus>(`/api/tasks/${id}`),
  approve: (id: string, allow: boolean) =>
    json<TaskStatus>(`/api/tasks/${id}/approve?allow=${allow}`, { method: "POST" }),
  cancel: (id: string) => json<TaskStatus>(`/api/tasks/${id}/cancel`, { method: "POST" }),
  browserState: () => json<{ url: string; title: string; screenshot: string; ready: boolean }>("/api/browser/state"),
  privacy: () => json<PrivacyStats>("/api/privacy/statistics"),
  performance: () => json<PerfStats>("/api/performance/statistics"),
  audit: () => json<Array<Record<string, unknown>>>("/api/audit/logs"),
  health: () => json<Record<string, unknown>>("/api/system/health"),
};
