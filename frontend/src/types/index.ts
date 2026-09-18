export type TaskStatus = {
  id: string;
  instruction: string;
  status: string;
  current_url: string;
  current_page: string;
  current_action: string;
  step: number;
  message: string;
  pending_confirmation?: {
    action: string;
    element_id?: string;
    value?: string;
    destination?: string;
    reason?: string;
  } | null;
  last_model_context?: unknown;
  last_action?: unknown;
  last_guard?: unknown;
};

export type PrivacyStats = {
  pii_detected_locally: number;
  pii_tokenized: number;
  raw_pii_sent_to_ai: number;
  sanitized_context_sent: boolean;
  blocked_actions: number;
};

export type PerfStats = {
  dom_scans: number;
  dom_processing_latency_ms: number;
  accessibility_processing_latency_ms: number;
  ocr_invocations: number;
  ocr_skipped: number;
  average_ocr_latency_ms: number;
  last_ocr_latency_ms: number;
  ocr_regions: number;
  last_ocr_reason: string;
  llm_calls: number;
  llm_latency_ms: number;
  agent_steps: number;
  blocked_actions: number;
  completed_actions: number;
  ocr_events?: Array<Record<string, unknown>>;
  ocr_model_load_count?: number;
};
