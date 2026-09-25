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
    const interactiveSelectors = 'a, button, input, select, textarea, [role="button"], [role="link"], [tabindex]:not([tabindex="-1"])';
    const nodes = document.querySelectorAll(interactiveSelectors);

    nodes.forEach((node, index) => {
        // Generate a unique ID if it doesn't have one
        const elId = node.id || `vlite-el-${index}`;
        if (!node.id) node.id = elId;

        const rect = node.getBoundingClientRect();
        
        // Skip hidden elements
        if (rect.width === 0 || rect.height === 0 || window.getComputedStyle(node).visibility === 'hidden') {
            return;
        }

        // Apply Redaction!
        let isSensitive = sensitiveNodes.has(node);
        let rawText = (node.innerText || '').trim().substring(0, 100);
        let rawValue = (node.value || '').trim().substring(0, 100);
        let rawPlaceholder = (node.placeholder || '').trim().substring(0, 100);

        if (isSensitive) {
            rawValue = "[REDACTED_SENSITIVE_INPUT]";
        } else if (window.PrivacyScanner) {
            // Scrub free-text
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

// Execute action requested by the backend
function executeAction(action) {
    if (!action || !action.action) return false;

    chrome.runtime.sendMessage({ type: 'LOG', text: `Executing: ${action.action} on ${action.element_id || 'page'}`, level: 'info' });

    if (action.action === 'finish') {
        chrome.runtime.sendMessage({ type: 'TASK_COMPLETE' });
        return true;
    }

    if (!action.element_id) return false;
    
    const target = document.getElementById(action.element_id);
    if (!target) {
        chrome.runtime.sendMessage({ type: 'LOG', text: `Element ${action.element_id} not found.`, level: 'error' });
        return false;
    }

    // Scroll into view
    target.scrollIntoView({ behavior: 'smooth', block: 'center' });

    if (action.action === 'click') {
        target.click();
        return true;
    }

    if (action.action === 'fill') {
        target.value = action.value;
        target.dispatchEvent(new Event('input', { bubbles: true }));
        target.dispatchEvent(new Event('change', { bubbles: true }));
        return true;
    }

    return false;
}

// Listen for messages from popup or background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "START_AGENT") {
        sendResponse({ status: "started" });
        
        chrome.runtime.sendMessage({ type: 'LOG', text: 'Extracting DOM state...' });
        const domState = extractDOM();
        
        // Send state to background script to make API call
        chrome.runtime.sendMessage({ 
            action: "CALL_BACKEND", 
            task: request.task,
            dom: domState
        });
    }

    if (request.action === "EXECUTE_ACTION") {
        const success = executeAction(request.payload);
        sendResponse({ success });
        
        // If it was a click or fill, trigger next step after a short delay
        if (success && request.payload.action !== 'finish') {
            setTimeout(() => {
                chrome.runtime.sendMessage({ type: 'LOG', text: 'Re-evaluating page state...' });
                const newDomState = extractDOM();
                chrome.runtime.sendMessage({ 
                    action: "CALL_BACKEND", 
                    task: request.task, // Needs to be preserved in real app
                    dom: newDomState
                });
            }, 2000);
        }
    }
    return true; // Keeps message channel open
});
