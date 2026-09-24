document.addEventListener('DOMContentLoaded', () => {
    const taskInput = document.getElementById('taskInput');
    const runBtn = document.getElementById('runBtn');
    const btnText = document.getElementById('btnText');
    const btnLoader = document.getElementById('btnLoader');
    const statusLog = document.getElementById('statusLog');

    function log(message, type = 'system') {
        const p = document.createElement('p');
        p.className = `log-entry ${type}`;
        p.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        statusLog.appendChild(p);
        statusLog.scrollTop = statusLog.scrollHeight;
    }

    function setRunning(isRunning) {
        runBtn.disabled = isRunning;
        taskInput.disabled = isRunning;
        if (isRunning) {
            btnText.textContent = 'Running...';
            btnLoader.classList.remove('hidden');
        } else {
            btnText.textContent = 'Run Agent';
            btnLoader.classList.add('hidden');
        }
    }

    runBtn.addEventListener('click', async () => {
        const task = taskInput.value.trim();
        if (!task) {
            log('Please enter a task.', 'error');
            return;
        }

        setRunning(true);
        log(`Starting task: "${task}"`, 'info');

        try {
            // Get the active tab
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            if (!tab) {
                throw new Error("No active tab found.");
            }
            
            log('Starting agent...', 'system');
            
            // Tell background script to start the agent so it can track navigation
            chrome.runtime.sendMessage({ 
                action: "START_AGENT_FROM_POPUP", 
                task: task,
                tabId: tab.id
            });

        } catch (error) {
            log(`Error: ${error.message}`, 'error');
            setRunning(false);
        }
    });
    
    // Listen for messages from background/content scripts for logging
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        if (message.type === 'LOG') {
            log(message.text, message.level || 'system');
        } else if (message.type === 'TASK_COMPLETE') {
            log('Task completed successfully!', 'success');
            setRunning(false);
        } else if (message.type === 'TASK_FAILED') {
            log(`Task failed: ${message.reason}`, 'error');
            setRunning(false);
        }
    });
});
