// VisiLite Privacy Scanner
// Highly optimized, zero-dependency heuristics + regex engine for Phase 2

const PrivacyScanner = {
    // 1. Lightweight Regex Patterns for Free-Text (High Precision)
    PATTERNS: {
        EMAIL: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g,
        PHONE_US: /\b(?:\+?1[-. ]?)?\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})\b/g,
        PHONE_IN: /\b(?:\+?91[\-\s]?)?[6789]\d{9}\b/g, // Indian Mobile (+91 9876543210)
        SSN: /\b\d{3}-\d{2}-\d{4}\b/g,
        AADHAAR: /\b\d{4}\s?\d{4}\s?\d{4}\b/g, // Indian Aadhaar (1234 5678 9012)
        PAN_CARD: /\b[A-Z]{5}\d{4}[A-Z]{1}\b/g, // Indian PAN (ABCDE1234F)
        UPI_ID: /\b[a-zA-Z0-9.\-_]{3,}@[a-zA-Z]{3,}\b/g, // Indian UPI (name@okicici)
        CREDIT_CARD: /\b(?:\d[ -]*?){13,16}\b/g,
        IP_ADDRESS: /\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b/g,
        CRYPTO_WALLET: /\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b|\b0x[a-fA-F0-9]{40}\b/g
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
        sanitized = sanitized.replace(this.PATTERNS.AADHAAR, '[REDACTED_AADHAAR]');
        sanitized = sanitized.replace(this.PATTERNS.PAN_CARD, '[REDACTED_PAN]');
        sanitized = sanitized.replace(this.PATTERNS.UPI_ID, '[REDACTED_UPI]');
        sanitized = sanitized.replace(this.PATTERNS.EMAIL, '[REDACTED_EMAIL]');
        sanitized = sanitized.replace(this.PATTERNS.PHONE_US, '[REDACTED_PHONE]');
        sanitized = sanitized.replace(this.PATTERNS.PHONE_IN, '[REDACTED_PHONE]');
        sanitized = sanitized.replace(this.PATTERNS.IP_ADDRESS, '[REDACTED_IP]');
        sanitized = sanitized.replace(this.PATTERNS.CRYPTO_WALLET, '[REDACTED_WALLET]');
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
            
            // Visual Style (Premium Frosted Glass Blur)
            overlay.style.backgroundColor = 'rgba(150, 150, 150, 0.2)';
            overlay.style.backdropFilter = 'blur(6px)';
            overlay.style.webkitBackdropFilter = 'blur(6px)';
            overlay.style.borderRadius = '4px';
            overlay.style.zIndex = '2147483647'; // Max z-index
            
            // Hover-to-reveal logic for the judges (interactive demo trick)
            overlay.style.transition = 'opacity 0.2s';
            overlay.style.pointerEvents = 'auto'; // Catch mouse events
            overlay.style.cursor = 'help';
            
            overlay.addEventListener('mouseenter', (e) => {
                if (e.shiftKey) overlay.style.opacity = '0'; // Hold Shift to reveal!
            });
            overlay.addEventListener('mouseleave', () => {
                overlay.style.opacity = '1';
            });
            
            document.body.appendChild(overlay);
        });
    }
};

window.PrivacyScanner = PrivacyScanner;
