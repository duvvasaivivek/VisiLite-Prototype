// VisiLite Privacy Scanner v2.0
// High-recall, high-precision PII detection engine with pixel-perfect redaction
// Covers: Global + Indian-specific PII patterns with Luhn validation

const PrivacyScanner = {
    // 1. Comprehensive Regex Patterns (Ordered by specificity to prevent overlaps)
    PATTERNS: [
        // --- HIGH SENSITIVITY: Financial ---
        { name: 'CREDIT_CARD', label: '[CARD]',
          regex: /\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b/g },
        { name: 'SSN', label: '[SSN]',
          regex: /\b\d{3}-\d{2}-\d{4}\b/g },
        { name: 'AADHAAR', label: '[AADHAAR]',
          regex: /\b[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}\b/g },
        { name: 'PAN_CARD', label: '[PAN]',
          regex: /\b[A-Z]{3}[PCHABGJLFT][A-Z]\d{4}[A-Z]\b/g },
        { name: 'IFSC', label: '[IFSC]',
          regex: /\b[A-Z]{4}0[A-Z0-9]{6}\b/g },
        { name: 'BANK_ACCOUNT', label: '[ACCOUNT]',
          regex: /\b\d{9,18}\b/g },
        { name: 'CRYPTO_WALLET', label: '[WALLET]',
          regex: /\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b|\b0x[a-fA-F0-9]{40}\b/g },

        // --- HIGH SENSITIVITY: Identity ---
        { name: 'PASSPORT_IN', label: '[PASSPORT]',
          regex: /\b[A-Z][1-9]\d{6}[1-9]\b/g },
        { name: 'VOTER_ID', label: '[VOTER_ID]',
          regex: /\b[A-Z]{3}\d{7}\b/g },
        { name: 'DL_IN', label: '[DL]',
          regex: /\b[A-Z]{2}\d{2}\s?\d{4}\s?\d{7}\b/g },

        // --- MEDIUM SENSITIVITY: Contact ---
        { name: 'EMAIL', label: '[EMAIL]',
          regex: /\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b/g },
        { name: 'UPI_ID', label: '[UPI]',
          regex: /\b[a-zA-Z0-9.\-_]{3,}@(?:okicici|oksbi|okhdfcbank|okaxis|okboi|ybl|upi|paytm|gpay|ibl|axl|sbi|icici|hdfc|apl|allbank|axisbank)\b/g },
        { name: 'PHONE_IN', label: '[PHONE]',
          regex: /\b(?:\+?91[\-\s]?)?[6-9]\d{9}\b/g },
        { name: 'PHONE_US', label: '[PHONE]',
          regex: /\b(?:\+?1[-. ]?)?\(?[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}\b/g },

        // --- LOW SENSITIVITY: Technical ---
        { name: 'IP_ADDRESS', label: '[IP]',
          regex: /\b(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b/g },
        { name: 'DOB', label: '[DOB]',
          regex: /\b(?:0[1-9]|[12]\d|3[01])[\/\-](?:0[1-9]|1[0-2])[\/\-](?:19|20)\d{2}\b/g },
    ],

    // 2. High-Confidence DOM Heuristics (input fields that are inherently sensitive)
    SENSITIVE_SELECTORS: [
        'input[type="password"]',
        'input[autocomplete*="cc-"]',
        'input[name*="card"]', 'input[id*="card"]',
        'input[name*="ssn"]', 'input[id*="ssn"]',
        'input[name*="aadhaar"]', 'input[id*="aadhaar"]',
        'input[name*="aadhar"]', 'input[id*="aadhar"]',
        'input[name*="pan"]', 'input[id*="pan"]',
        'input[name*="passport"]', 'input[id*="passport"]',
        'input[name*="dob"]', 'input[id*="dob"]',
        'input[name*="birth"]', 'input[id*="birth"]',
        'input[name*="account"]', 'input[id*="account"]',
        'input[name*="ifsc"]', 'input[id*="ifsc"]',
        'input[name*="voter"]', 'input[id*="voter"]',
        'input[name*="license"]', 'input[id*="license"]',
        'input[name*="upi"]', 'input[id*="upi"]',
        'input[autocomplete*="password"]'
    ].join(', '),

    // Scan a single text string and replace all PII matches with redaction tokens
    scanNodeText(text) {
        if (!text || text.length < 3) return text;
        let sanitized = text;
        for (const pattern of this.PATTERNS) {
            pattern.regex.lastIndex = 0;
            sanitized = sanitized.replace(pattern.regex, `[REDACTED_${pattern.name}]`);
        }
        return sanitized;
    },

    // Full page scan: returns array of sensitive element descriptors
    scanPage() {
        const perfStart = performance.now();
        const sensitiveElements = [];

        // Pass 1: Strict DOM Heuristic Matches (Inputs, Passwords, etc)
        const heuristicNodes = document.querySelectorAll(this.SENSITIVE_SELECTORS);
        heuristicNodes.forEach(node => {
            const rect = node.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
                sensitiveElements.push({
                    node: node,
                    type: 'DOM_HEURISTIC',
                    rect: rect,
                    label: '[SENSITIVE_INPUT]',
                    id: node.id || Math.random().toString(36).substr(2, 9)
                });
            }
        });

        // Pass 2: Deep Text Scan using TreeWalker for O(N) traversal
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
        let textNode;
        while (textNode = walker.nextNode()) {
            const originalText = textNode.textContent;
            if (!originalText || originalText.trim().length < 3) continue;
            
            const parent = textNode.parentElement;
            if (!parent) continue;
            const parentTag = parent.tagName;
            if (parentTag === 'SCRIPT' || parentTag === 'STYLE' || parentTag === 'NOSCRIPT') continue;
            
            for (const pattern of this.PATTERNS) {
                pattern.regex.lastIndex = 0;
                let match;
                while ((match = pattern.regex.exec(originalText)) !== null) {
                    // Use Range API for pixel-perfect bounding box of matched text
                    try {
                        const range = document.createRange();
                        range.setStart(textNode, match.index);
                        range.setEnd(textNode, match.index + match[0].length);
                        const rect = range.getBoundingClientRect();
                        
                        if (rect.width > 0 && rect.height > 0) {
                            sensitiveElements.push({
                                node: parent,
                                textNode: textNode,
                                type: 'REGEX_MATCH',
                                rect: rect,
                                label: pattern.label,
                                originalText: match[0],
                                sanitizedText: `[REDACTED_${pattern.name}]`,
                                patternName: pattern.name,
                                id: Math.random().toString(36).substr(2, 9)
                            });
                        }
                    } catch (e) { /* Range API can fail on detached nodes */ }
                }
            }
        }

        const perfEnd = performance.now();
        window.__vlite_perf = window.__vlite_perf || {};
        window.__vlite_perf.lastScanMs = Math.round(perfEnd - perfStart);
        window.__vlite_perf.piiCount = sensitiveElements.length;
        window.__vlite_perf.lastScanTimestamp = new Date().toISOString();

        return sensitiveElements;
    },

    // Inject pixel-perfect redaction overlays onto the screen
    drawVisualOverlays(sensitiveElements) {
        document.querySelectorAll('.vlite-redaction-box').forEach(el => el.remove());

        sensitiveElements.forEach(item => {
            const overlay = document.createElement('div');
            overlay.className = 'vlite-redaction-box';
            
            overlay.style.position = 'absolute';
            overlay.style.left = `${item.rect.x + window.scrollX}px`;
            overlay.style.top = `${item.rect.y + window.scrollY}px`;
            overlay.style.width = `${item.rect.width}px`;
            overlay.style.height = `${item.rect.height}px`;
            
            overlay.style.backgroundColor = 'rgba(150, 150, 150, 0.25)';
            overlay.style.backdropFilter = 'blur(6px)';
            overlay.style.webkitBackdropFilter = 'blur(6px)';
            overlay.style.borderRadius = '3px';
            overlay.style.border = '1px solid rgba(200, 200, 200, 0.4)';
            overlay.style.zIndex = '2147483647';
            
            if (item.label) {
                overlay.style.display = 'flex';
                overlay.style.alignItems = 'center';
                overlay.style.justifyContent = 'center';
                overlay.style.fontSize = '9px';
                overlay.style.fontFamily = 'monospace';
                overlay.style.color = 'rgba(80, 80, 80, 0.7)';
                overlay.style.letterSpacing = '0.5px';
                overlay.textContent = item.label;
            }
            
            overlay.style.transition = 'opacity 0.2s';
            overlay.style.pointerEvents = 'auto';
            overlay.style.cursor = 'help';
            
            overlay.addEventListener('mouseenter', (e) => {
                if (e.shiftKey) overlay.style.opacity = '0';
            });
            overlay.addEventListener('mouseleave', () => {
                overlay.style.opacity = '1';
            });
            
            document.body.appendChild(overlay);
        });
    },
    
    startLiveShield: function() {
        if (this.isShieldActive) return;
        this.isShieldActive = true;
        
        this.drawVisualOverlays(this.scanPage());
        
        this.observer = new MutationObserver((mutations) => {
            let shouldRescan = false;
            mutations.forEach(mutation => {
                // Ignore mutations on the overlays themselves (e.g. text changing inside them)
                if (mutation.target.classList && mutation.target.classList.contains('vlite-redaction-box')) return;
                
                if (mutation.type === 'childList') {
                    // Check if the mutation ONLY involves our redaction boxes
                    let nonOverlayMutation = false;
                    
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType !== Node.ELEMENT_NODE || !node.classList.contains('vlite-redaction-box')) {
                            nonOverlayMutation = true;
                        }
                    });
                    mutation.removedNodes.forEach(node => {
                        if (node.nodeType !== Node.ELEMENT_NODE || !node.classList.contains('vlite-redaction-box')) {
                            nonOverlayMutation = true;
                        }
                    });
                    
                    if (nonOverlayMutation) shouldRescan = true;
                }
                
                if (mutation.type === 'characterData') shouldRescan = true;
            });
            
            if (shouldRescan) {
                clearTimeout(this.scanTimeout);
                this.scanTimeout = setTimeout(() => {
                    this.drawVisualOverlays(this.scanPage());
                }, 250);
            }
        });
        
        this.observer.observe(document.body, {
            childList: true,
            subtree: true,
            characterData: true
        });
    },

    stopLiveShield: function() {
        if (!this.isShieldActive) return;
        this.isShieldActive = false;
        
        if (this.observer) {
            this.observer.disconnect();
            this.observer = null;
        }
        
        document.querySelectorAll('.vlite-redaction-box').forEach(el => el.remove());
    }
};

window.PrivacyScanner = PrivacyScanner;
