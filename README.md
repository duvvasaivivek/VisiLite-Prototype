# VisiLite

Privacy-Preserving Visual Agent for Secure Web Automation.

VisiLite places a **local privacy enforcement gateway** between the user's browser and the AI reasoning layer. The model receives only sanitized, task-relevant context. Sensitive values stay in a local token vault and are resolved at the Action Guard immediately before the Chrome extension executes an action.

This prototype does **not** claim perfect privacy, zero risk, or coverage of every website. It demonstrates a measurable boundary: for the included local workflows, raw protected profile values are not placed in the model request payload.

## Architecture

```
USER → UI → Task Orchestrator → Chrome Extension
    → Local perception (DOM + accessibility, OCR fallback)
    → Privacy gateway (PII detection, tokenization, policy, vault)
    → Sanitized context → AI reasoner (structured JSON only)
    → Action Guard → local token resolution → browser action (via extension) → observe
```

Trusted locally: browser adapter, DOM/a11y, OCR, PII detection, vault, policy, action guard, audit logs.

Untrusted: cloud LLM (if configured), external websites, webpage text (prompt-injection treated as data).

## Requirements

- Python 3.11+
- Node.js 20+
- Ordinary CPU laptop (no GPU required)

Optional:

- EasyOCR (`requirements/optional.txt`) for visual-only fallback
- Microsoft Presidio if `ENABLE_PRESIDIO=true`

## Quick start

```bash
cd "VisiLite - Prototype"
copy .env.example .env

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements/backend.txt

cd backend
set PYTHONPATH=.
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

The backend also starts local test sites on http://localhost:3000

### LLM configuration

`.env`:

```
LLM_PROVIDER=local
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=
```

- `LLM_PROVIDER=local` uses a deterministic planner that **only** sees sanitized structured context (no raw vault values). This is for CPU-only demos without API credits.
- `LLM_PROVIDER=openai` plus `LLM_API_KEY` sends the same sanitized JSON to OpenAI. If the key is missing, the UI/API reports `AI reasoning unavailable` and does not bypass the privacy gateway.

Never hardcode credentials.

## Primary demo

Task: `Fill the registration form using my saved details.`

The agent:

1. Opens http://localhost:3000/registration
2. Extracts DOM + accessibility data
3. Detects PII and tokenizes values already in the local profile/vault
4. Sends sanitized context to the reasoner
5. Validates JSON actions in Action Guard
6. Resolves tokens locally (`<EMAIL_001>` → `john@example.com`)
7. Fills and submits the form via the Chrome extension
8. Records real privacy/performance metrics

Inspect **Model Context Inspector**. Protected raw values from the vault must not appear there.

## Other demos

- `/attack` — webpage prompt injection is untrusted and cannot override policy.
- `/visual` — coupon text lives on a canvas; OCR is a fallback, not a per-iteration scan.
- `/shopping` and `/banking` — high-risk submits require confirmation.

## Tests

```bash
set PYTHONPATH=backend
set VISILITE_SKIP_BROWSER=1
set VISILITE_SKIP_TEST_SITES=1
pytest tests/unit tests/security tests/integration
```

## Benchmarks

Start the backend (test sites + extension) first.

*Note: Playwright-based benchmarking was removed as it was unused and broke the intended Chrome extension architecture.*

Results are written to `benchmarks/last_e2e.json` and `benchmarks/last_run.json` from **actual runs**.

Mode A (naive) runs full-frame OCR every perception pass. Mode B (optimized) uses DOM/a11y, perception caching, and OCR only when needed.

## API

- `POST /api/tasks`
- `GET /api/tasks/{id}`
- `POST /api/tasks/{id}/approve`
- `POST /api/tasks/{id}/cancel`
- `GET /api/browser/state`
- `POST /api/privacy/analyze`
- `POST /api/privacy/sanitize`
- `POST /api/agent/plan`
- `POST /api/actions/validate`
- `POST /api/actions/execute`
- `GET /api/audit/logs`
- `GET /api/privacy/statistics`
- `GET /api/performance/statistics`
- `GET /api/system/health`

## Domain allowlist (V1)

Only `localhost` and `127.0.0.1` by default. `javascript:`, `file:`, and unknown hosts are blocked.

## Docker

```bash
docker compose up --build
```

## What is intentionally local

PII detection, tokenization, policy checks, action validation, and audit logging do not depend on a cloud LLM. If reasoning is unavailable, the system fails closed rather than sending raw page state off-box.
