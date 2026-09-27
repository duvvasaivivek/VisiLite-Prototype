let activeTask = null;
let activeTabId = null;
let actionHistory = [];
let currentAbortController = null;

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "START_AGENT_FROM_POPUP") {
        activeTask = request.task;
        activeTabId = request.tabId;
        actionHistory = []; // Reset history for new task
        
        chrome.tabs.sendMessage(activeTabId, { 
            action: "START_AGENT", 
            task: activeTask 
        }, (response) => {
            if (chrome.runtime.lastError) {
                 chrome.runtime.sendMessage({ type: 'LOG', text: 'Error: Please refresh the webpage (F5) to inject the extension!', level: 'error' });
                 chrome.runtime.sendMessage({ type: 'TASK_FAILED', reason: 'Content script missing. Page needs refresh.' });
                 activeTask = null;
            }
        });
        return true;
    }

    if (request.action === "CALL_BACKEND") {
        const backendUrl = "http://127.0.0.1:8000/api/plan";
        
        if (currentAbortController) {
            currentAbortController.abort();
        }
        currentAbortController = new AbortController();
        
        chrome.runtime.sendMessage({ type: 'LOG', text: 'Sending sanitized DOM to backend...' });

        fetch(backendUrl, {
            method: 'POST',
            signal: currentAbortController.signal,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task: request.task,
                context: request.dom,
                history: actionHistory
            })
        })
        .then(res => {
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            return res.json();
        })
        .then(data => {
            if (!activeTask) return; // Drop zombie responses if task was finished/failed
            
            chrome.runtime.sendMessage({ type: 'LOG', text: 'Received action plan from AI.', level: 'success' });
            actionHistory.push(`${data.action} on ${data.element_id}`);
            
            if (sender.tab && sender.tab.id) {
                chrome.tabs.sendMessage(sender.tab.id, {
                    action: "EXECUTE_ACTION",
                    task: request.task,
                    payload: data
                });
            }
        })
        .catch(error => {
            if (error.name === 'AbortError') return; // Ignore aborted requests
            
            chrome.runtime.sendMessage({ type: 'LOG', text: `Backend connection failed: ${error.message}`, level: 'error' });
            chrome.runtime.sendMessage({ type: 'TASK_FAILED', reason: error.message });
            activeTask = null;
        });

        return true;
    }

    if (request.type === 'TASK_COMPLETE' || request.type === 'TASK_FAILED') {
        activeTask = null; // Clear task when finished
    }
});

// Resume task if the page navigates!
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (activeTask && tabId === activeTabId && changeInfo.status === 'complete') {
        chrome.runtime.sendMessage({ type: 'LOG', text: 'Page loaded. Resuming task...', level: 'system' });
        
        // Wait a second for DOM to settle, then re-inject
        setTimeout(() => {
            chrome.tabs.sendMessage(tabId, { 
                action: "START_AGENT", 
                task: activeTask 
            });
        }, 1000);
    }
});
