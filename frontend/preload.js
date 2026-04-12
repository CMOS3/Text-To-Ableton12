const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
    /**
     * Pings the FastAPI backend to verify connectivity.
     * @returns {Promise<Object>} The backend session status or error.
     */
    /**
     * Pings the FastAPI backend to verify connectivity.
     * @param {string} baseUrl - The base URL of the FastAPI backend.
     * @returns {Promise<Object>} The backend session status or error.
     */
    ping: async (baseUrl) => {
        try {
            const response = await fetch(`${baseUrl}/api/session`);
            if (!response.ok) {
                throw new Error(`Backend response error: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to ping backend:', error);
            throw error;
        }
    },
    /**
     * Sends a chat message to the FastAPI backend.
     * @param {string} prompt - The user's message.
     * @param {string} baseUrl - The base URL of the FastAPI backend.
     * @returns {Promise<Object>} The AI's response.
     */
    sendChatMessage: async (prompt, baseUrl, chatHistory = []) => {
        try {
            const response = await fetch(`${baseUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt, chat_history: chatHistory }),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Backend response error: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to send chat message:', error);
            throw error;
        }
    }
});
