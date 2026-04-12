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
    sendChatMessage: async (prompt, baseUrl, chatHistory = [], onChunk) => {
        try {
            const response = await fetch(`${baseUrl}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt, chat_history: chatHistory }),
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Backend response error: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';
            let finalData = null;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                let lines = buffer.split('\n');
                buffer = lines.pop(); // keep remainder
                for (let line of lines) {
                    if (line.trim()) {
                        try {
                            const parsed = JSON.parse(line);
                            if (parsed.type === 'final') finalData = parsed.data;
                            if (onChunk) onChunk(parsed);
                        } catch (error) {
                            console.warn("Skipping malformed chunk:", line, error);
                            continue;
                        }
                    }
                }
            }
            if (buffer.trim()) {
                try {
                    const parsed = JSON.parse(buffer);
                    if (parsed.type === 'final') finalData = parsed.data;
                    if (onChunk) onChunk(parsed);
                } catch (error) {
                    console.warn("Skipping malformed chunk:", buffer, error);
                }
            }
            return finalData;
        } catch (error) {
            console.error('Failed to send chat message:', error);
            throw error;
        }
    }
});
