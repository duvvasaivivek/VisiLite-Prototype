// Extract basic DOM elements that the agent can interact with
function extractDOM() {
    // 1. Run the Privacy Scanner FIRST
    const sensitiveElements = window.PrivacyScanner ? window.PrivacyScanner.scanPage() : [];
    if (window.PrivacyScanner) {
        window.PrivacyScanner.drawVisualOverlays(sensitiveElements);
    }
    
    // Create a fast lookup Set for DOM heuristic elements
    const sensitiveNodes = new Set(sensitiveElements.filter(e => e.type === 'DOM_HEURISTIC').map(e => e.node));

    if (sensitiveElements.length > 0) {
        let hiddenDetails = sensitiveElements.map(e => {
            if (e.type === 'REGEX_MATCH') return `"${e.originalText}"`;
            return `<${e.node.tagName.toLowerCase()} type="${e.node.type || ''}">`;
        }).join(', ');
        chrome.runtime.sendMessage({ type: 'LOG', text: `Privacy Shield: Redacted ${sensitiveElements.length} items (${hiddenDetails})`, level: 'success' });
    }

    const elements = [];
    
    // We only care about interactive elements or text content
    const interactiveSelectors = 'a, button, input, select, textarea, [role="button"], [role="link"], [role="textbox"], [contenteditable="true"], [tabindex]:not([tabindex="-1"])';
    const nodes = document.querySelectorAll(interactiveSelectors);

    nodes.forEach((node) => {
        // Generate a stable unique ID that survives DOM re-evaluations
        let elId = node.id || node.getAttribute('data-vlite-id');
        if (!elId) {
            elId = `vlite-el-${Math.random().toString(36).substr(2, 9)}`;
            node.setAttribute('data-vlite-id', elId);
        }

        const rect = node.getBoundingClientRect();
        
        // Skip hidden elements
        if (rect.width === 0 || rect.height === 0 || window.getComputedStyle(node).visibility === 'hidden') {
            return;
        }

        let isSensitive = sensitiveNodes.has(node);
        let rawText = (node.innerText || '').trim().substring(0, 100);
        let rawValue = node.isContentEditable ? (node.innerText || '').trim().substring(0, 100) : (node.value || '').trim().substring(0, 100);
        let rawPlaceholder = (node.placeholder || '').trim().substring(0, 100);

        if (isSensitive) {
            rawValue = "[REDACTED_SENSITIVE_INPUT]";
        } else if (window.PrivacyScanner) {
            rawText = window.PrivacyScanner.scanNodeText(rawText);
            rawValue = window.PrivacyScanner.scanNodeText(rawValue);
            rawPlaceholder = window.PrivacyScanner.scanNodeText(rawPlaceholder);
        }

        elements.push({
            id: elId,
            tag: node.tagName.toLowerCase(),
            type: node.type || null,
            role: node.getAttribute('role') || null,
            text: rawText,
            value: rawValue,
            placeholder: rawPlaceholder,
            boundingBox: {
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height
            }
        });
    });

    return {
        url: window.location.href,
        title: document.title,
        elements: elements
    };
}

let ghostCursor = null;
function createGhostCursor() {
    if (ghostCursor) return ghostCursor;
    ghostCursor = document.createElement('div');
    ghostCursor.style.position = 'fixed';
    ghostCursor.style.width = '24px';
    ghostCursor.style.height = '24px';
    
    // SVG of a standard mouse cursor pointer
    const cursorSvg = `<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'><path d='M7 2l12 11.2-5.8.5 3.3 7.3-2.25 1-3.2-7.4-4.4 4.7z' fill='black' stroke='white' stroke-width='1.5'/></svg>`;
    ghostCursor.style.backgroundImage = `url("data:image/svg+xml;utf8,${cursorSvg}")`;
    ghostCursor.style.backgroundSize = 'contain';
    ghostCursor.style.backgroundRepeat = 'no-repeat';
    
    ghostCursor.style.pointerEvents = 'none';
    ghostCursor.style.zIndex = '99999999';
    // Smooth transition for moving and for the 'click press' scale effect
    ghostCursor.style.transition = 'top 0.5s ease-in-out, left 0.5s ease-in-out, transform 0.1s';
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
        cursor.style.top = `${rect.top + rect.height/2}px`;
        cursor.style.left = `${rect.left + rect.width/2}px`;
        setTimeout(() => resolve(), 600);
    });
}

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
        await new Promise(r => setTimeout(r, Math.random() * 50 + 30));
    }
    element.dispatchEvent(new Event('change', { bubbles: true }));
}

// Execute action requested by the backend
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

    if (!action.element_id) return false;
    
    const target = document.getElementById(action.element_id) || document.querySelector(`[data-vlite-id="${action.element_id}"]`);
    if (!target) {
        chrome.runtime.sendMessage({ type: 'LOG', text: `Element ${action.element_id} not found.`, level: 'error' });
        return false;
    }

    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    await new Promise(r => setTimeout(r, 300));
    
    await moveCursorTo(target);

    if (action.action === 'click') {
        ghostCursor.style.transform = 'scale(0.8)';
        await new Promise(r => setTimeout(r, 150));
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

// Listen for messages from popup or background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "START_AGENT") {
        sendResponse({ status: "started" });
        
        chrome.runtime.sendMessage({ type: 'LOG', text: 'Extracting DOM state...' });
        
        // Start the Privacy Shield only when the agent is running
        if (window.PrivacyScanner) window.PrivacyScanner.startLiveShield();
        const domState = extractDOM();
        
        // Send state to background script to make API call
        chrome.runtime.sendMessage({ 
            action: "CALL_BACKEND", 
            task: request.task,
            dom: domState
        });
    }

    if (request.action === "EXECUTE_ACTION") {
        executeAction(request.payload).then(success => {
            sendResponse({ success });
            
            // If it was a click or fill, wait for page to settle
            if (success && request.payload.action !== 'finish' && request.payload.action !== 'fail') {
                // Remove the sluggish document.readyState check. Modern SPAs update the DOM instantly.
                // We just need a snappy 800ms wait for UI animations to finish before taking the next snapshot.
                setTimeout(() => {
                    chrome.runtime.sendMessage({ type: 'LOG', text: 'Re-evaluating page state...' });
                    const newDomState = extractDOM();
                    chrome.runtime.sendMessage({ 
                        action: "CALL_BACKEND", 
                        task: request.task,
                        dom: newDomState
                    });
                }, 800);
            } else if (request.payload.action === 'finish' || request.payload.action === 'fail') {
                // Stop the Privacy Shield when the agent is done
                if (window.PrivacyScanner) window.PrivacyScanner.stopLiveShield();
                
                // Remove the ghost cursor
                if (ghostCursor) {
                    ghostCursor.remove();
                    ghostCursor = null;
                }
            }
        });
    }
    return true; // Keeps message channel open
});
