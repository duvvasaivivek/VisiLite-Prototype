# Architecture

See the README for the runtime pipeline. Modules:

- `backend/app/browser` — Playwright adapter (no model-direct control)
- `backend/app/perception` — DOM, accessibility, cached perception, EasyOCR singleton
- `backend/app/privacy` — hybrid PII, vault, sanitizer, profile
- `backend/app/policy` — transmission and confirmation policy
- `backend/app/security` — domain allowlist, prompt-injection handling
- `backend/app/agent` — LLM/local planner, Action Guard, orchestrator loop
- `backend/app/audit` — redacted event log
- `test-sites` — local demo websites
