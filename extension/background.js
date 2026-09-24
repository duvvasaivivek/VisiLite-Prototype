chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "CALL_BACKEND") {
        
        const backendUrl = "http://127.0.0.1:8000/api/plan"; // We will build this endpoint next
        
        chrome.runtime.sendMessage({ type: 'LOG', text: 'Sending sanitized DOM to backend...' });

        fetch(backendUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                task: request.task,
                context: request.dom
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            chrome.runtime.sendMessage({ type: 'LOG', text: 'Received action plan from AI.', level: 'success' });
            
            // Send the action back to the content script to execute
            chrome.tabs.sendMessage(sender.tab.id, {
                action: "EXECUTE_ACTION",
                task: request.task,
                payload: data
            });
        })
        .catch(error => {
            chrome.runtime.sendMessage({ type: 'LOG', text: `Backend connection failed: ${error.message}. Is the Python server running?`, level: 'error' });
            chrome.runtime.sendMessage({ type: 'TASK_FAILED', reason: error.message });
        });

        return true; // Keep message channel open for async fetch
    }
});
