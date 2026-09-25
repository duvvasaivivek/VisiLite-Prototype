// VisiLite Privacy Scanner
// Highly optimized, zero-dependency heuristics + regex engine for Phase 2

const PrivacyScanner = {
    // 1. Lightweight Regex Patterns for Free-Text (High Precision)
    PATTERNS: {
        EMAIL: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g,
        PHONE: /\b(?:\+?1[-. ]?)?\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})\b/g,
        SSN: /\b\d{3}-\d{2}-\d{4}\b/g,
        CREDIT_CARD: /\b(?:\d[ -]*?){13,16}\b/g, // Simplified heuristic for CC
    },

    // 2. High-Confidence DOM Heuristics (High Recall, 0 latency)
    SENSITIVE_SELECTORS: [
        'input[type="password"]',
        'input[autocomplete*="cc-"]',
        'input[name*="card"]',
        'input[id*="card"]',
        'input[name*="ssn"]',
        'input[id*="ssn"]',
        'input[autocomplete*="password"]'
    ].join(', '),

    scanNodeText(text) {
        if (!text) return text;
        let sanitized = text;
        sanitized = sanitized.replace(this.PATTERNS.CREDIT_CARD, '[REDACTED_CARD]');
        sanitized = sanitized.replace(this.PATTERNS.SSN, '[REDACTED_SSN]');
        sanitized = sanitized.replace(this.PATTERNS.EMAIL, '[REDACTED_EMAIL]');
        sanitized = sanitized.replace(this.PATTERNS.PHONE, '[REDACTED_PHONE]');
        return sanitized;
    },

    // Returns a map of sensitive elements and their exact bounding boxes
    scanPage() {
        const sensitiveElements = [];

        // Pass 1: Strict Heuristic Matches (Inputs, Passwords, etc)
        const heuristicNodes = document.querySelectorAll(this.SENSITIVE_SELECTORS);
        heuristicNodes.forEach(node => {
            const rect = node.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
                sensitiveElements.push({
                    node: node,
                    type: 'DOM_HEURISTIC',
                    rect: rect,
                    id: node.id || Math.random().toString(36).substr(2, 9)
                });
            }
        });

        // Pass 2: Deep Text Scan (Visible text nodes & labels)
        // We scan all elements that might contain text
        const textNodes = document.querySelectorAll('p, span, div, label, td, th, li, a');
        textNodes.forEach(node => {
            // Only scan if it has direct text content to avoid scanning huge container divs
            if (node.childNodes.length === 1 && node.childNodes[0].nodeType === Node.TEXT_NODE) {
                const originalText = node.innerText || node.textContent;
                if (!originalText) return;

                const sanitized = this.scanNodeText(originalText);
                
                if (sanitized !== originalText) {
                    const rect = node.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        sensitiveElements.push({
                            node: node,
                            type: 'REGEX_MATCH',
                            rect: rect,
                            originalText: originalText,
                            sanitizedText: sanitized,
                            id: node.id || Math.random().toString(36).substr(2, 9)
                        });
                    }
                }
            }
        });

        return sensitiveElements;
    },

    // Inject physical black boxes onto the screen for the judges
    drawVisualOverlays(sensitiveElements) {
        // Clear old overlays
        document.querySelectorAll('.vlite-redaction-box').forEach(el => el.remove());

        sensitiveElements.forEach(item => {
            const overlay = document.createElement('div');
            overlay.className = 'vlite-redaction-box';
            
            // Exact bounding box mapping
            overlay.style.position = 'absolute';
            overlay.style.left = `${item.rect.x + window.scrollX}px`;
            overlay.style.top = `${item.rect.y + window.scrollY}px`;
            overlay.style.width = `${item.rect.width}px`;
            overlay.style.height = `${item.rect.height}px`;
            
            // Visual Style (Solid Black Box)
            overlay.style.backgroundColor = 'black';
            overlay.style.zIndex = '2147483647'; // Max z-index
            overlay.style.pointerEvents = 'none'; // Don't block clicks
            
            document.body.appendChild(overlay);
        });
    }
};

window.PrivacyScanner = PrivacyScanner;
