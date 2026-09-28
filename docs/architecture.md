# Architecture

See the README for the runtime pipeline. Modules:

- `extension/` — Chrome extension (content script for DOM extraction and action execution)
- `backend/app/perception` — DOM, accessibility, cached perception, EasyOCR singleton
- `backend/app/privacy` — hybrid PII, vault, sanitizer, profile
- `backend/app/policy` — transmission and confirmation policy
- `backend/app/security` — domain allowlist, prompt-injection handling
- `backend/app/agent` — LLM/local planner, Action Guard, orchestrator loop
- `backend/app/audit` — redacted event log
- `test-sites` — local demo websites
