const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
    /**
     * Pings the FastAPI backend to verify connectivity.
     * @returns {Promise<Object>} The backend session status or error.
     */
    ping: async () => {
        try {
            const response = await fetch('http://127.0.0.1:8000/api/session');
            if (!response.ok) {
                throw new Error(`Backend response error: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to ping backend:', error);
            throw error;
        }
    }
});
