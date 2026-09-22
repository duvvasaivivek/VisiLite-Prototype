const BASE_URL = "http://127.0.0.1:8000/api";

export const POLLING_INTERVALS = {
  TASK: 1500,
  PRIVACY_STATS: 2000,
  HEALTH: 5000
};

export interface TaskCreate {
  instruction: string;
  start_url?: string;
}

export interface TaskStatus {
  id: string;
  instruction: string;
  status: "idle" | "running" | "awaiting_confirmation" | "completed" | "failed" | "cancelled" | "blocked";
  current_url: string;
  current_page: string;
  current_action: string;
  step: number;
  message: string;
  pending_confirmation?: any;
  last_model_context?: any;
  last_action?: any;
  last_guard?: any;
}

export interface PrivacyStats {
  pii_detected_locally: number;
  pii_tokenized: number;
  raw_pii_sent_to_ai: number;
  sanitized_context_sent: boolean;
  blocked_actions: number;
}

export interface HealthResponse {
  status: string;
  llm_provider: string;
  llm_available: boolean;
  ocr_enabled: boolean;
  ocr_loaded: boolean;
  browser_ready: boolean;
  privacy_gateway: string;
}

export const api = {
  createTask: async (task: TaskCreate): Promise<TaskStatus> => {
    const res = await fetch(`${BASE_URL}/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(task),
    });
    return res.json();
  },

  getTask: async (taskId: string): Promise<TaskStatus> => {
    const res = await fetch(`${BASE_URL}/tasks/${taskId}`);
    return res.json();
  },

  approveAction: async (taskId: string, allow: boolean): Promise<{status: string}> => {
    const res = await fetch(`${BASE_URL}/tasks/${taskId}/approve?allow=${allow}`, {
      method: "POST",
    });
    return res.json();
  },

  getPrivacyStats: async (): Promise<PrivacyStats> => {
    const res = await fetch(`${BASE_URL}/privacy/statistics`);
    return res.json();
  },

  getHealth: async (): Promise<HealthResponse> => {
    const res = await fetch(`${BASE_URL}/system/health`);
    return res.json();
  }
};
