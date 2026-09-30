# VisiLite

**Privacy-Preserving Visual Agent for Secure Web Automation**

VisiLite is a production-grade AI web agent architecture designed with a **zero-trust privacy boundary**. Instead of blindly scraping your screen and sending it to a cloud LLM, VisiLite places a local privacy enforcement gateway between the user's browser and the AI reasoning layer. 

The LLM receives only sanitized, highly-optimized context. Sensitive values (like credit cards or passwords) stay locked in a local AES-256 encrypted vault. The AI reasons using "tokens" (e.g., `<VAULT_TOKEN: Phone Number>`), which are resolved locally at the very last millisecond before the Chrome extension executes the action.

## 🚀 Key Features

- **"Zero-Trust" Two-Tier Privacy Engine**: PII is actively hunted and redacted right inside the browser's DOM by the Chrome Extension. As a zero-trust fallback, the backend runs a secondary hybrid scrubbing pass before any data touches the LLM.
- **Cryptographic Vault Tokenization**: Sensitive profile data is encrypted via AES-256. The LLM never sees your real data, only semantic tokens.
- **Chain-of-Thought (CoT) Reasoning**: VisiLite uses a highly engineered JSON schema that forces the Gemini model to output a `thought` reasoning block before taking any action, drastically improving its success rate on complex web tasks.
- **Aggressive Token Optimization**: DOM trees are massive. Our custom serialization algorithm strips empty attributes, null values, invisible elements, and JSON whitespace, cutting API token payloads by ~60% without losing semantic context.
- **Production-Ready Resiliency**: Built to handle global cloud API outages. If Google's servers throw a `503 High Demand` or `429` error, VisiLite engages an automatic exponential backoff sequence to seamlessly retry the reasoning step without crashing your session.
- **Native Chrome Extension**: Completely free of heavy, bot-flagged automation frameworks like Playwright. VisiLite operates stealthily via a lightweight HTTP bridge to a native Chrome Extension.

## 🏗️ Architecture

```text
USER → UI → Task Orchestrator 
    → Chrome Extension (DOM/a11y Extraction + Frontend Redaction)
    → Backend API (Privacy Gateway + Vault Unlock)
    → Token Optimization & CoT Prompting
    → Cloud LLM (Gemini API - Structured JSON only)
    → Action Guard (Risk Assessment)
    → Local Token Resolution
    → Chrome Extension (Executes Action)
```

## 🛠️ Quick Start

### 1. Requirements
- Python 3.10+
- Node.js 20+
- Google Chrome (or Chromium-based browser)

### 2. Backend Setup
```bash
cd "VisiLite - Prototype"
copy .env.example .env
```
Edit your `.env` file to include your Gemini API credentials and a secure vault password:
```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-flash-latest
LLM_API_KEY=your_gemini_api_key_here
VAULT_PASSWORD=your_secure_password
```

Install dependencies and run the server:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements/backend.txt

cd backend
set PYTHONPATH=.
uvicorn app.main:app --reload --port 8000
```
*(The backend also automatically hosts local test sites on `http://localhost:3000`)*

### 3. Frontend Setup
In a second terminal:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

### 4. Chrome Extension Setup (Required)
Since VisiLite uses a native extension to bypass bot-detection:
1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** in the top right corner.
3. Click **Load unpacked** and select the `extension` folder inside this repository.
4. Pin the VisiLite extension to your browser toolbar.

## 🧪 Running the Test Suite

VisiLite includes a rigorous security and unit testing suite to ensure privacy boundaries are never breached. 

To run the tests, ensure your terminal has the correct environment variables to bypass the browser constraints:
```bash
set PYTHONPATH=backend
set VISILITE_SKIP_BROWSER=1
set VISILITE_SKIP_TEST_SITES=1
pytest tests/ -q
```

## 🛡️ Security Guarantees (Intentionally Local)

The following components **never** depend on a cloud LLM:
- PII detection and masking
- AES-256 Vault Encryption/Decryption
- Tokenization mapping
- Action risk assessment (Action Guard)
- Audit logging

If the AI reasoning API goes down, the system **fails closed**. It will never send raw page state off-box to attempt a bypass.
