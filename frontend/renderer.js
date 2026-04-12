const pingBtn = document.getElementById('ping-btn');
const responseLog = document.getElementById('response-log');
const statusIndicator = document.getElementById('status-indicator');

pingBtn.addEventListener('click', async () => {
    responseLog.textContent = 'Pinging backend...';
    pingBtn.disabled = true;

    try {
        const data = await window.api.ping();
        
        // Success
        responseLog.textContent = JSON.stringify(data, null, 2);
        statusIndicator.textContent = 'Connected';
        statusIndicator.classList.remove('offline');
        statusIndicator.classList.add('online');
    } catch (error) {
        // Failure
        responseLog.textContent = `Error: ${error.message}\nMake sure your FastAPI server is running at http://127.0.0.1:8000`;
        statusIndicator.textContent = 'Disconnected';
        statusIndicator.classList.remove('online');
        statusIndicator.classList.add('offline');
    } finally {
        pingBtn.disabled = false;
    }
});

// Optional: Auto-ping on load
window.addEventListener('DOMContentLoaded', () => {
    pingBtn.click();
});
