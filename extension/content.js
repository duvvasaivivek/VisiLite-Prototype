// VisiLite Content Script v2.0
// DOM Grounding Engine — extracts rich semantic context and executes AI actions

// ──────────────────────────────────────────────
// 1. DOM EXTRACTION (Metric 1: Visual Context Accuracy — 25%)
// ──────────────────────────────────────────────
function extractDOM() {
    const perfStart = performance.now();

    // 1a. Run the Privacy Scanner FIRST
    const sensitiveElements = window.PrivacyScanner ? window.PrivacyScanner.scanPage() : [];
    
    const sensitiveNodes = new Set(sensitiveElements.filter(e => e.type === 'DOM_HEURISTIC').map(e => e.node));

    if (sensitiveElements.length > 0) {
        let hiddenDetails = sensitiveElements.map(e => {
            if (e.type === 'REGEX_MATCH') return `${e.label}`;
            return `<${e.node.tagName.toLowerCase()}>`;
        }).join(', ');
        chrome.runtime.sendMessage({ type: 'LOG', text: `Privacy Shield: Redacted ${sensitiveElements.length} items (${hiddenDetails})`, level: 'success' });
    }

    const elements = [];
    
    // 1b. Rich selector set — includes ARIA roles and contenteditable
    const interactiveSelectors = 'a, button, input, select, textarea, [role="button"], [role="link"], [role="textbox"], [role="menuitem"], [role="tab"], [role="checkbox"], [role="radio"], [role="combobox"], [role="searchbox"], [contenteditable="true"], [tabindex]:not([tabindex="-1"])';
    const nodes = document.querySelectorAll(interactiveSelectors);

    // 1c. Resolve <label for="..."> associations into a map
    const labelMap = {};
    document.querySelectorAll('label[for]').forEach(lbl => {
        labelMap[lbl.getAttribute('for')] = (lbl.textContent || '').trim().substring(0, 80);
    });

    nodes.forEach((node) => {
        // Stable ID anchoring (survives SPA re-renders)
        let elId = node.id || node.getAttribute('data-vlite-id');
        if (!elId) {
            elId = `vlite-el-${Math.random().toString(36).substr(2, 9)}`;
            node.setAttribute('data-vlite-id', elId);
        }

        const rect = node.getBoundingClientRect();
        
        if (rect.width === 0 || rect.height === 0) return;
        const style = window.getComputedStyle(node);
        if (style.visibility === 'hidden' || style.display === 'none' || style.opacity === '0') return;

        let isSensitive = sensitiveNodes.has(node);
        let rawText = (node.textContent || '').trim().substring(0, 120);
        let rawValue = node.isContentEditable 
            ? (node.textContent || '').trim().substring(0, 120) 
            : (node.value || '').trim().substring(0, 120);
        let rawPlaceholder = (node.placeholder || '').trim().substring(0, 80);

        if (isSensitive) {
            rawValue = "[REDACTED_SENSITIVE_INPUT]";
        } else if (window.PrivacyScanner) {
            rawText = window.PrivacyScanner.scanNodeText(rawText);
            rawValue = window.PrivacyScanner.scanNodeText(rawValue);
            rawPlaceholder = window.PrivacyScanner.scanNodeText(rawPlaceholder);
        }

        // 1d. Extract rich semantic attributes for AI grounding
        const ariaLabel = node.getAttribute('aria-label') || '';
        const ariaDescribedBy = node.getAttribute('aria-describedby');
        let describedByText = '';
        if (ariaDescribedBy) {
            const descEl = document.getElementById(ariaDescribedBy);
            if (descEl) describedByText = (descEl.textContent || '').trim().substring(0, 80);
        }

        const resolvedLabel = labelMap[node.id] || '';

        elements.push({
            id: elId,
            tag: node.tagName.toLowerCase(),
            type: node.type || null,
            role: node.getAttribute('role') || null,
            name: node.name || null,
            text: rawText,
            value: rawValue,
            placeholder: rawPlaceholder,
            ariaLabel: ariaLabel || null,
            label: resolvedLabel || null,
            describedBy: describedByText || null,
            href: node.tagName === 'A' ? (node.href || null) : null,
            checked: node.checked !== undefined ? node.checked : null,
            disabled: node.disabled || false,
            boundingBox: {
                x: Math.round(rect.x),
                y: Math.round(rect.y),
                width: Math.round(rect.width),
                height: Math.round(rect.height)
            }
        });
    });

    // 1e. Page text sample for contextual awareness
    const bodyText = (document.body.textContent || '').trim();
    let pageTextSample = bodyText.substring(0, 500);
    if (window.PrivacyScanner) {
        pageTextSample = window.PrivacyScanner.scanNodeText(pageTextSample);
    }

    const perfEnd = performance.now();
    window.__vlite_perf = window.__vlite_perf || {};
    window.__vlite_perf.lastExtractMs = Math.round(perfEnd - perfStart);
    window.__vlite_perf.elementCount = elements.length;

    // Draw the overlays AFTER all layout reads (getBoundingClientRect/getComputedStyle) are complete to prevent layout thrashing
    if (window.PrivacyScanner) {
        window.PrivacyScanner.drawVisualOverlays(sensitiveElements);
    }

    return {
        url: window.location.href,
        title: document.title,
        elements: elements,
        pageTextSample: pageTextSample,
        elementCount: elements.length
    };
}

// ──────────────────────────────────────────────
// 2. GHOST CURSOR
// ──────────────────────────────────────────────
let ghostCursor = null;
function createGhostCursor() {
    if (ghostCursor) return ghostCursor;
    ghostCursor = document.createElement('div');
    ghostCursor.style.position = 'fixed';
    ghostCursor.style.width = '24px';
    ghostCursor.style.height = '24px';
    
    const cursorSvg = `<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'><path d='M7 2l12 11.2-5.8.5 3.3 7.3-2.25 1-3.2-7.4-4.4 4.7z' fill='black' stroke='white' stroke-width='1.5'/></svg>`;
    ghostCursor.style.backgroundImage = `url("data:image/svg+xml;utf8,${cursorSvg}")`;
    ghostCursor.style.backgroundSize = 'contain';
    ghostCursor.style.backgroundRepeat = 'no-repeat';
    
    ghostCursor.style.pointerEvents = 'none';
    ghostCursor.style.zIndex = '99999999';
    ghostCursor.style.transition = 'top 0.35s ease-in-out, left 0.35s ease-in-out, transform 0.1s';
    ghostCursor.style.top = '50%';
    ghostCursor.style.left = '50%';
    ghostCursor.style.transform = 'scale(1)';
    document.body.appendChild(ghostCursor);
    return ghostCursor;
}

function moveCursorTo(element) {
    return new Promise(resolve => {
        const cursor = createGhostCursor();
        const rect = element.getBoundingClientRect();
        cursor.style.top = `${rect.top + rect.height / 2}px`;
        cursor.style.left = `${rect.left + rect.width / 2}px`;
        setTimeout(() => resolve(), 400);
    });
}

// ──────────────────────────────────────────────
// 3. TYPING ENGINE
// ──────────────────────────────────────────────
async function typeText(element, text) {
    const isEditable = element.isContentEditable;
    
    if (isEditable) {
        element.focus();
        document.execCommand('selectAll', false, null);
        document.execCommand('delete', false, null);
    } else {
        element.value = '';
    }

    for (let i = 0; i < text.length; i++) {
        if (isEditable) {
            document.execCommand('insertText', false, text[i]);
        } else {
            element.value += text[i];
            element.dispatchEvent(new Event('input', { bubbles: true }));
        }
        await new Promise(r => setTimeout(r, Math.random() * 40 + 25));
    }
    element.dispatchEvent(new Event('change', { bubbles: true }));
}

// ──────────────────────────────────────────────
// 4. ACTION EXECUTION ENGINE
// ──────────────────────────────────────────────
async function executeAction(action) {
    if (!action || !action.action) return false;

    chrome.runtime.sendMessage({ type: 'LOG', text: `Executing: ${action.action} on ${action.element_id || 'page'}`, level: 'info' });

    if (action.action === 'finish') {
        chrome.runtime.sendMessage({ type: 'TASK_COMPLETE' });
        if (ghostCursor) { ghostCursor.remove(); ghostCursor = null; }
        return true;
    }

    if (action.action === 'fail') {
        chrome.runtime.sendMessage({ type: 'TASK_FAILED', reason: action.reason || 'AI determined the task cannot be completed.' });
        if (ghostCursor) { ghostCursor.remove(); ghostCursor = null; }
        return true;
    }

    if (action.action === 'navigate' && action.url) {
        window.location.href = action.url;
        return true;
    }

    if (action.action === 'scroll') {
        const amount = parseInt(action.value) || 300;
        window.scrollBy({ top: amount, behavior: 'smooth' });
        return true;
    }

    if (!action.element_id) return false;
    
    const target = document.getElementById(action.element_id) || document.querySelector(`[data-vlite-id="${action.element_id}"]`);
    if (!target) {
        chrome.runtime.sendMessage({ type: 'LOG', text: `Element ${action.element_id} not found.`, level: 'error' });
        return false;
    }

    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    await new Promise(r => setTimeout(r, 200));
    
    await moveCursorTo(target);

    if (action.action === 'click') {
        ghostCursor.style.transform = 'scale(0.8)';
        await new Promise(r => setTimeout(r, 120));
        target.click();
        ghostCursor.style.transform = 'scale(1)';
        return true;
    }

    if (action.action === 'fill' || action.action === 'select') {
        if (target.tagName === 'SELECT') {
            target.value = action.value;
            target.dispatchEvent(new Event('change', { bubbles: true }));
        } else {
            await typeText(target, action.value);
        }
        return true;
    }
    
    if (action.action === 'enter') {
        target.focus();
        target.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
        target.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
        return true;
    }

    return false;
}

// ──────────────────────────────────────────────
// 5. MESSAGE ROUTER
// ──────────────────────────────────────────────
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "START_AGENT") {
        sendResponse({ status: "started" });
        
        chrome.runtime.sendMessage({ type: 'LOG', text: 'Extracting DOM state...' });
        
        if (window.PrivacyScanner) window.PrivacyScanner.startLiveShield();
        const domState = extractDOM();
        
        chrome.runtime.sendMessage({ 
            action: "CALL_BACKEND", 
            task: request.task,
            dom: domState
        });
    }

    if (request.action === "EXECUTE_ACTION") {
        const stepStart = performance.now();
        
        executeAction(request.payload).then(success => {
            sendResponse({ success });
            
            const stepMs = Math.round(performance.now() - stepStart);
            window.__vlite_perf = window.__vlite_perf || {};
            window.__vlite_perf.lastStepMs = stepMs;
            
            if (success && request.payload.action !== 'finish' && request.payload.action !== 'fail') {
                const initialUrl = window.location.href;
                setTimeout(() => {
                    if (window.location.href !== initialUrl) {
                        chrome.runtime.sendMessage({ type: 'LOG', text: 'Navigation detected. Yielding to page load handler...', level: 'system' });
                        return;
                    }
                    chrome.runtime.sendMessage({ type: 'LOG', text: 'Re-evaluating page state...' });
                    const newDomState = extractDOM();
                    chrome.runtime.sendMessage({ 
                        action: "CALL_BACKEND", 
                        task: request.task,
                        dom: newDomState
                    });
                }, 700);
            } else if (request.payload.action === 'finish' || request.payload.action === 'fail') {
                if (window.PrivacyScanner) window.PrivacyScanner.stopLiveShield();
                
                if (ghostCursor) {
                    ghostCursor.remove();
                    ghostCursor = null;
                }
            }
        });
    }
    return true;
});
