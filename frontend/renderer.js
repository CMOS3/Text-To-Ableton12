const chatHistory = document.getElementById('chat-history');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const clearBtn = document.getElementById('clear-btn');
const statusIndicator = document.getElementById('status-indicator');

// Settings DOM
const settingsBtn = document.getElementById('settings-btn');
const settingsModal = document.getElementById('settings-modal');
const backendUrlInput = document.getElementById('backend-url-input');
const genreInput = document.getElementById('genre-input');
const macroNameInput = document.getElementById('macro-name-input');
const macroPromptInput = document.getElementById('macro-prompt-input');
const addMacroBtn = document.getElementById('add-macro-btn');
const macroList = document.getElementById('macro-list');
const quickLaunchBar = document.getElementById('quick-launch-bar');
const settingsSaveBtn = document.getElementById('settings-save-btn');
const settingsCancelBtn = document.getElementById('settings-cancel-btn');

// State
let backendUrl = localStorage.getItem('backendUrl') || 'http://127.0.0.1:8000';
let currentGenre = localStorage.getItem('currentGenre') || '';
let savedMacros = JSON.parse(localStorage.getItem('savedMacros') || '[]');
let chatHistoryArray = [];
let costFlash = 0.0;
let costPro = 0.0;
let flashTokens = 0;
let proTokens = 0;

const costFlashM = document.getElementById('cost-flash');
const costProM = document.getElementById('cost-pro');

/**
 * Basic Markdown Parser using Regex.
 * @param {string} text - Raw markdown text.
 * @returns {string} - Parsed HTML.
 */
function parseMarkdown(text) {
    // 1. Escape HTML to prevent XSS
    let html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

    // 2. Multiline Code Blocks (```code```)
    html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');

    // 3. Bold (**text**)
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // 4. Italic (*text*)
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // 5. Line Breaks (\n)
    // We only replace \n with <br> if it's NOT inside a <pre> block
    const parts = html.split(/(<pre>[\s\S]*?<\/pre>)/g);
    html = parts.map(part => {
        if (part.startsWith('<pre>')) return part;
        return part.replace(/\n/g, '<br>');
    }).join('');

    return html;
}

/**
 * Renders the macro list in the settings modal and the quick actions bar.
 */
function renderMacros() {
    // 1. Render Settings Modal List
    macroList.innerHTML = '';
    savedMacros.forEach((macro, index) => {
        const item = document.createElement('div');
        item.className = 'macro-item';
        item.innerHTML = `
            <div class="macro-info">
                <span class="macro-name">${macro.name}</span>
                <span class="macro-payload">${macro.prompt}</span>
            </div>
            <button class="delete-macro-btn" data-index="${index}">Delete</button>
        `;
        macroList.appendChild(item);
    });

    // 2. Render Main UI Quick Actions
    quickLaunchBar.innerHTML = '';
    savedMacros.forEach((macro) => {
        const btn = document.createElement('button');
        btn.className = 'macro-btn';
        btn.textContent = macro.name;
        btn.title = macro.prompt;
        btn.addEventListener('click', () => {
            chatInput.value = macro.prompt;
            handleSendMessage();
        });
        quickLaunchBar.appendChild(btn);
    });

    // 3. Add Delete Listeners
    document.querySelectorAll('.delete-macro-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const index = parseInt(e.target.dataset.index);
            savedMacros.splice(index, 1);
            localStorage.setItem('savedMacros', JSON.stringify(savedMacros));
            renderMacros();
        });
    });
}

/**
 * Appends a message to the chat history.
 * @param {string} sender - 'user' or 'ai'
 * @param {string} text - The message content
 */
function appendMessage(sender, text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'bubble';
    
    if (sender === 'ai') {
        bubbleDiv.innerHTML = parseMarkdown(text);
    } else {
        bubbleDiv.textContent = text; // User input stays escaped
    }
    
    messageDiv.appendChild(bubbleDiv);
    chatHistory.appendChild(messageDiv);
    
    // Auto-scroll to bottom
    chatHistory.scrollTop = chatHistory.scrollHeight;
    
    return messageDiv;
}

// Event Listeners
clearBtn.addEventListener('click', () => {
    chatHistory.innerHTML = '';
    chatHistoryArray = [];
    costFlash = 0.0;
    costPro = 0.0;
    flashTokens = 0;
    proTokens = 0;
    costFlashM.textContent = `Flash: $0.0000 (0 tk)`;
    costProM.textContent = `Pro: $0.0000 (0 tk)`;
});

// Settings Logic
settingsBtn.addEventListener('click', () => {
    backendUrlInput.value = backendUrl;
    genreInput.value = currentGenre;
    renderMacros();
    settingsModal.classList.remove('hidden');
});

settingsCancelBtn.addEventListener('click', () => {
    settingsModal.classList.add('hidden');
});

settingsSaveBtn.addEventListener('click', () => {
    const newUrl = backendUrlInput.value.trim();
    const newGenre = genreInput.value.trim();
    
    backendUrl = newUrl || 'http://127.0.0.1:8000';
    currentGenre = newGenre || '';
    
    localStorage.setItem('backendUrl', backendUrl);
    localStorage.setItem('currentGenre', currentGenre);
    
    settingsModal.classList.add('hidden');
    checkConnection();
});

addMacroBtn.addEventListener('click', () => {
    const name = macroNameInput.value.trim();
    const prompt = macroPromptInput.value.trim();
    
    if (name && prompt) {
        savedMacros.push({ name, prompt });
        localStorage.setItem('savedMacros', JSON.stringify(savedMacros));
        macroNameInput.value = '';
        macroPromptInput.value = '';
        renderMacros();
    }
});

// Close modal when clicking outside the card
settingsModal.addEventListener('click', (e) => {
    if (e.target === settingsModal) {
        settingsModal.classList.add('hidden');
    }
});

/**
 * Shows the "Thinking..." indicator.
 * @returns {HTMLElement} The loading element
 */
function showThinking() {
    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'message ai';
    thinkingDiv.id = 'thinking-indicator';
    
    const thinkingContent = document.createElement('div');
    thinkingContent.className = 'bubble thinking';
    thinkingContent.textContent = 'Thinking';
    
    thinkingDiv.appendChild(thinkingContent);
    chatHistory.appendChild(thinkingDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    
    return thinkingDiv;
}

/**
 * Removes the "Thinking..." indicator.
 */
function removeThinking() {
    const indicator = document.getElementById('thinking-indicator');
    if (indicator) {
        indicator.remove();
    }
}

/**
 * Handles sending a message.
 */
async function handleSendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    // 1. Append user message
    const instruction = currentGenre ? `[Style: ${currentGenre}] ${text}` : text;
    appendMessage('user', text);
    chatHistoryArray.push({ role: "user", content: instruction });
    
    // 2. Clear and disable input
    chatInput.value = '';
    chatInput.disabled = true;
    sendBtn.disabled = true;

    // 3. Show thinking indicator
    showThinking();

    try {
        // 4. Call API with configured backendUrl
        const data = await window.api.sendChatMessage(text, backendUrl, chatHistoryArray);
        
        // 5. Success
        removeThinking();
        appendMessage('ai', data.response || "I couldn't process that request.");
        chatHistoryArray.push({ role: "assistant", content: data.response || "" });
        
        // Calculate cost
        if (data.model_used && data.input_tokens !== undefined && data.output_tokens !== undefined) {
            const totalTokens = data.input_tokens + data.output_tokens;
            if (data.model_used === 'FLASH') {
                const stepCost = (data.input_tokens / 1000000) * 0.25 + (data.output_tokens / 1000000) * 1.50;
                costFlash += stepCost;
                flashTokens += totalTokens;
                costFlashM.textContent = `Flash: $${costFlash.toFixed(4)} (${flashTokens} tk)`;
            } else if (data.model_used === 'PRO') {
                const stepCost = (data.input_tokens / 1000000) * 2.00 + (data.output_tokens / 1000000) * 12.00;
                costPro += stepCost;
                proTokens += totalTokens;
                costProM.textContent = `Pro: $${costPro.toFixed(4)} (${proTokens} tk)`;
            }
        }

        updateStatus(true);
    } catch (error) {
        // 6. Failure
        removeThinking();
        appendMessage('ai', `Error: ${error.message}. Please verify the Backend URL in Settings.`);
        updateStatus(false);
    } finally {
        // 7. Re-enable and focus
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

function updateStatus(isOnline) {
    if (isOnline) {
        statusIndicator.textContent = 'Online';
        statusIndicator.classList.remove('offline');
        statusIndicator.classList.add('online');
    } else {
        statusIndicator.textContent = 'Offline';
        statusIndicator.classList.remove('online');
        statusIndicator.classList.add('offline');
    }
}

async function checkConnection() {
    try {
        await window.api.ping(backendUrl);
        updateStatus(true);
    } catch (error) {
        updateStatus(false);
    }
}

// Event Listeners
sendBtn.addEventListener('click', handleSendMessage);

chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        handleSendMessage();
    }
});

// INITIALIZATION
window.addEventListener('DOMContentLoaded', () => {
    renderMacros();
    checkConnection();
    chatInput.focus();
});
