// VisiLite Privacy Scanner v2.1
// Context-Aware PII Engine: Separates candidate generation from classification
// Resolves false positives using surrounding DOM and text semantics

const PrivacyScanner = {
    // 1. Strict Patterns (Unambiguous, requires no context)
    PATTERNS: [
        { name: 'CREDIT_CARD', label: '[CARD]', regex: /\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b/g },
        { name: 'SSN', label: '[SSN]', regex: /\b\d{3}-\d{2}-\d{4}\b/g },
        { name: 'AADHAAR', label: '[AADHAAR]', regex: /\b[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}\b/g },
        { name: 'PAN_CARD', label: '[PAN]', regex: /\b[A-Z]{3}[PCHABGJLFT][A-Z]\d{4}[A-Z]\b/g },
        { name: 'IFSC', label: '[IFSC]', regex: /\b[A-Z]{4}0[A-Z0-9]{6}\b/g },
        { name: 'CRYPTO_WALLET', label: '[WALLET]', regex: /\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b|\b0x[a-fA-F0-9]{40}\b/g },
        { name: 'PASSPORT_IN', label: '[PASSPORT]', regex: /\b[A-Z][1-9]\d{6}[1-9]\b/g },
        { name: 'VOTER_ID', label: '[VOTER_ID]', regex: /\b[A-Z]{3}\d{7}\b/g },
        { name: 'DL_IN', label: '[DL]', regex: /\b[A-Z]{2}\d{2}\s?\d{4}\s?\d{7}\b/g },
        { name: 'EMAIL', label: '[EMAIL]', regex: /\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b/g },
        { name: 'UPI_ID', label: '[UPI]', regex: /\b[a-zA-Z0-9.\-_]{3,}@(?:okicici|oksbi|okhdfcbank|okaxis|okboi|ybl|upi|paytm|gpay|ibl|axl|sbi|icici|hdfc|apl|allbank|axisbank)\b/g },
        { name: 'IP_ADDRESS', label: '[IP]', regex: /\b(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b/g }
    ],

    // 2. Candidate Patterns (Ambiguous, requires text/DOM context resolution)
    CANDIDATE_PATTERNS: [
        { 
            name: 'NUMBER_CANDIDATE', 
            // Catches IN phones, US phones, and generic 9-18 digit IDs (Bank Accounts, Order IDs, Tracking IDs)
            regex: /\b(?:\+?1[-. ]?)?\(?[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}\b|\b(?:\+?91[\-\s]?)?[6-9]\d{9}\b|\b\d{9,18}\b/g 
        },
        { 
            name: 'DATE_CANDIDATE', 
            regex: /\b(?:0[1-9]|[12]\d|3[01])[\/\-](?:0[1-9]|1[0-2])[\/\-](?:19|20)\d{2}\b/g 
        }
    ],

    // 3. High-Confidence DOM Heuristics (input fields that are inherently sensitive)
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

    // Context-Aware Resolver: Classifies a candidate based on preceding text or parent DOM attributes
    resolveCandidate(matchString, candidateType, textBefore, nodeContext) {
        const combinedContext = (textBefore + " " + nodeContext).toLowerCase();
        
        if (candidateType === 'NUMBER_CANDIDATE') {
            // 1. Negative Context: Explicitly preserve safe identifiers
            if (/(order|invoice|tracking|txn|transaction|id|no\.|number|ref|receipt|item|part|qty|quantity)\b/i.test(combinedContext)) {
                return null; 
            }
            // 2. Positive Context: Phone Numbers
            if (/(phone|mobile|tel|cell|call|contact|sms|whatsapp|ph)\b/i.test(combinedContext)) {
                return { name: 'PHONE', label: '[PHONE]' };
            }
            // 3. Positive Context: Bank Accounts
            if (/(account|acct|bank|routing|ifsc|deposit|transfer)\b/i.test(combinedContext)) {
                return { name: 'BANK_ACCOUNT', label: '[ACCOUNT]' };
            }
            
            // 4. Default Heuristics (If no clear context exists)
            // US format fallback
            if (/\(?[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}/.test(matchString) && /[-()]/.test(matchString)) {
                return { name: 'PHONE', label: '[PHONE]' };
            }
            // IN format fallback (+91 prefix)
            if (/\+?91/.test(matchString)) {
                return { name: 'PHONE', label: '[PHONE]' };
            }
            
            // If it is just a random 10-18 digit number with no context, preserve it (prevent false positives on IDs)
            return null; 
        }
        
        if (candidateType === 'DATE_CANDIDATE') {
            if (/(dob|birth|born|age)\b/i.test(combinedContext)) {
                return { name: 'DOB', label: '[DOB]' };
            }
            // Event date, invoice date, delivery date, etc -> Preserve
            return null; 
        }
        
        return null;
    },

    // Scan a single text string (used by backend grounder)
    scanNodeText(text, contextStr = '') {
        if (!text || text.length < 3) return text;
        let sanitized = text;
        
        // 1. Strict Patterns
        for (const pattern of this.PATTERNS) {
            pattern.regex.lastIndex = 0;
            sanitized = sanitized.replace(pattern.regex, `[REDACTED_${pattern.name}]`);
        }
        
        // 2. Candidate Patterns (with context)
        for (const candidate of this.CANDIDATE_PATTERNS) {
            candidate.regex.lastIndex = 0;
            sanitized = sanitized.replace(candidate.regex, (matchStr, offset, fullStr) => {
                const textBefore = fullStr.substring(Math.max(0, offset - 40), offset);
                const resolved = this.resolveCandidate(matchStr, candidate.name, textBefore, contextStr);
                if (resolved) {
                    return `[REDACTED_${resolved.name}]`;
                }
                return matchStr; // preserve
            });
        }
        return sanitized;
    },

    // Full page scan: returns array of sensitive element descriptors for live redaction
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
            
            // Generate semantic context from the parent element to resolve candidates
            const nodeContext = [parent.id, parent.name, parent.className, parent.getAttribute('aria-label')].filter(Boolean).join(' ');

            // Sub-routine to push redaction rects
            const addRedaction = (matchStr, matchIndex, label, name) => {
                try {
                    const range = document.createRange();
                    range.setStart(textNode, matchIndex);
                    range.setEnd(textNode, matchIndex + matchStr.length);
                    const rect = range.getBoundingClientRect();
                    
                    if (rect.width > 0 && rect.height > 0) {
                        sensitiveElements.push({
                            node: parent,
                            textNode: textNode,
                            type: 'REGEX_MATCH',
                            rect: rect,
                            label: label,
                            originalText: matchStr,
                            sanitizedText: `[REDACTED_${name}]`,
                            patternName: name,
                            id: Math.random().toString(36).substr(2, 9)
                        });
                    }
                } catch (e) { /* Range API can fail on detached nodes */ }
            };
            
            // Evaluate Strict Patterns
            for (const pattern of this.PATTERNS) {
                pattern.regex.lastIndex = 0;
                let match;
                while ((match = pattern.regex.exec(originalText)) !== null) {
                    addRedaction(match[0], match.index, pattern.label, pattern.name);
                }
            }

            // Evaluate Context-Aware Candidate Patterns
            for (const candidate of this.CANDIDATE_PATTERNS) {
                candidate.regex.lastIndex = 0;
                let match;
                while ((match = candidate.regex.exec(originalText)) !== null) {
                    const textBefore = originalText.substring(Math.max(0, match.index - 45), match.index);
                    const resolved = this.resolveCandidate(match[0], candidate.name, textBefore, nodeContext);
                    if (resolved) {
                        addRedaction(match[0], match.index, resolved.label, resolved.name);
                    }
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
