const chatHistory = document.getElementById('chat-history');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const clearBtn = document.getElementById('clear-btn');
const statusIndicator = document.getElementById('status-indicator');

// Settings DOM
const settingsBtn = document.getElementById('settings-btn');
const settingsModal = document.getElementById('settings-modal');
const sessionGenreInput = document.getElementById('session-genre-input');
const geminiApiKeyInput = document.getElementById('gemini-api-key-input');
const mcpPortInput = document.getElementById('mcp-port-input');
const userLibraryPathInput = document.getElementById('user-library-path-input');
const browseLibraryBtn = document.getElementById('browse-library-btn');
const deployScriptBtn = document.getElementById('deploy-script-btn');
const optimizerShortcutInput = document.getElementById('optimizer-shortcut-input');
const settingsSaveBtn = document.getElementById('settings-save-btn');
const settingsCancelBtn = document.getElementById('settings-cancel-btn');
const restartAppBtn = document.getElementById('restart-app-btn');

// Session Drawer DOM
const sessionDrawer = document.getElementById('session-drawer');
const sessionDrawerToggleBtn = document.getElementById('session-drawer-toggle');
const closeDrawerBtn = document.getElementById('close-drawer-btn');
const inspectorBpm = document.getElementById('inspector-bpm');
const inspectorKey = document.getElementById('inspector-key');
const inspectorTracks = document.getElementById('inspector-tracks');
const refreshSessionBtn = document.getElementById('refresh-session-btn');

// History Drawer DOM
const historyDrawer = document.getElementById('history-drawer');
const historyDrawerToggleBtn = document.getElementById('history-drawer-toggle');
const closeHistoryDrawerBtn = document.getElementById('close-history-drawer-btn');
const historyList = document.getElementById('history-list');

// State
const backendUrl = 'http://127.0.0.1:8000';
let currentSessionGenre = '';
let geminiApiKey = localStorage.getItem('geminiApiKey') || '';
let mcpPort = parseInt(localStorage.getItem('mcpPort')) || 9877;
let userLibraryPath = localStorage.getItem('userLibraryPath') || '';
let optimizerShortcut = localStorage.getItem('optimizerShortcut') || 'Ctrl+E';
let requireApproval = localStorage.getItem('requireApproval') !== 'false'; // default true
const requireApprovalToggle = document.getElementById('require-approval-toggle');
if (requireApprovalToggle) {
    requireApprovalToggle.checked = requireApproval;
}
let chatHistoryArray = [];
let currentSessionId = null;
let currentSessionTitle = null;
let costFlash = 0.0;
let costPro = 0.0;
let flashTokens = 0;
let proTokens = 0;
let historyFlashCost = parseFloat(localStorage.getItem('historyFlashCost') || '0.0');
let historyProCost = parseFloat(localStorage.getItem('historyProCost') || '0.0');

const costFlashM = document.getElementById('cost-flash');
const costProM = document.getElementById('cost-pro');
const historyFlashM = document.getElementById('history-flash');
const historyProM = document.getElementById('history-pro');
const resetHistoryBtn = document.getElementById('reset-history-btn');
const costPromptFlashM = document.getElementById('cost-prompt-flash');
const costPromptProM = document.getElementById('cost-prompt-pro');

// Drawer Toggle Logic
if (sessionDrawerToggleBtn) {
    sessionDrawerToggleBtn.addEventListener('click', () => {
        sessionDrawer.classList.toggle('closed');
        if (!sessionDrawer.classList.contains('closed')) {
            historyDrawer.classList.add('closed');
            document.body.classList.add('drawer-open');
        } else {
            document.body.classList.remove('drawer-open');
        }
    });
}

if (closeDrawerBtn) {
    closeDrawerBtn.addEventListener('click', () => {
        sessionDrawer.classList.add('closed');
        document.body.classList.remove('drawer-open');
    });
}

if (historyDrawerToggleBtn) {
    historyDrawerToggleBtn.addEventListener('click', () => {
        historyDrawer.classList.toggle('closed');
        // Ensure the session drawer is closed if we open history
        if (!historyDrawer.classList.contains('closed')) {
            sessionDrawer.classList.add('closed');
            document.body.classList.add('drawer-open');
            loadHistoryList();
        } else {
            document.body.classList.remove('drawer-open');
        }
    });
}

if (closeHistoryDrawerBtn) {
    closeHistoryDrawerBtn.addEventListener('click', () => {
        historyDrawer.classList.add('closed');
        document.body.classList.remove('drawer-open');
    });
}

historyFlashM.textContent = `Flash: $${historyFlashCost.toFixed(4)}`;
historyProM.textContent = `Pro: $${historyProCost.toFixed(4)}`;

historyFlashM.textContent = `Flash: $${historyFlashCost.toFixed(4)}`;
historyProM.textContent = `Pro: $${historyProCost.toFixed(4)}`;

resetHistoryBtn.addEventListener('click', () => {
    historyFlashCost = 0.0;
    historyProCost = 0.0;
    localStorage.setItem('historyFlashCost', '0.0');
    localStorage.setItem('historyProCost', '0.0');
    historyFlashM.textContent = `Flash: $0.0000`;
    historyProM.textContent = `Pro: $0.0000`;
});

// Removed custom parseMarkdown, using marked.parse instead

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
        bubbleDiv.innerHTML = marked.parse(text);
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
    currentSessionId = null;
    currentSessionTitle = null;
    currentSessionGenre = '';
    if (sessionGenreInput) sessionGenreInput.value = '';
    costFlash = 0.0;
    costPro = 0.0;
    flashTokens = 0;
    proTokens = 0;
    if (costPromptFlashM) costPromptFlashM.textContent = `Flash: $0.0000`;
    if (costPromptProM) costPromptProM.textContent = `Pro: $0.0000`;
    costFlashM.textContent = `Flash: $0.0000`;
    costProM.textContent = `Pro: $0.0000`;
});

// Settings Logic
settingsBtn.addEventListener('click', () => {
    if (geminiApiKeyInput) geminiApiKeyInput.value = geminiApiKey;
    if (mcpPortInput) mcpPortInput.value = mcpPort;
    if (userLibraryPathInput) userLibraryPathInput.value = userLibraryPath;
    settingsModal.classList.remove('hidden');
});

settingsCancelBtn.addEventListener('click', () => {
    settingsModal.classList.add('hidden');
});

settingsSaveBtn.addEventListener('click', async () => {
    if (geminiApiKeyInput) {
        geminiApiKey = geminiApiKeyInput.value.trim();
        localStorage.setItem('geminiApiKey', geminiApiKey);
    }
    if (mcpPortInput) {
        mcpPort = parseInt(mcpPortInput.value.trim()) || 9877;
        localStorage.setItem('mcpPort', mcpPort.toString());
    }
    if (userLibraryPathInput) {
        userLibraryPath = userLibraryPathInput.value.trim();
        localStorage.setItem('userLibraryPath', userLibraryPath);
    }
    
    if (requireApprovalToggle) {
        requireApproval = requireApprovalToggle.checked;
        localStorage.setItem('requireApproval', requireApproval.toString());
    }
    
    settingsModal.classList.add('hidden');
    
    try {
        await fetch(`${backendUrl}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ gemini_api_key: geminiApiKey, mcp_port: mcpPort })
        });
    } catch (e) {
        console.warn("Failed to update backend settings:", e);
    }
    
    checkConnection();
});

if (restartAppBtn) {
    restartAppBtn.addEventListener('click', () => {
        if (window.api && window.api.restartApp) {
            window.api.restartApp();
        }
    });
}

if (browseLibraryBtn) {
    browseLibraryBtn.addEventListener('click', async () => {
        if (window.api && window.api.selectFolder) {
            const folder = await window.api.selectFolder();
            if (folder) {
                userLibraryPathInput.value = folder;
            }
        }
    });
}

if (deployScriptBtn) {
    deployScriptBtn.addEventListener('click', async () => {
        const dest = userLibraryPathInput.value.trim();
        if (!dest) {
            alert("Please provide an Ableton User Library Path first.");
            return;
        }
        if (window.api && window.api.deployRemoteScript) {
            deployScriptBtn.disabled = true;
            deployScriptBtn.textContent = "Deploying...";
            try {
                const result = await window.api.deployRemoteScript(dest);
                if (result.success) {
                    alert("Deployment successful! Please refresh your Ableton Live Browser or restart Ableton Live.");
                } else {
                    alert("Deployment failed: " + result.message);
                }
            } catch (e) {
                alert("Error during deployment: " + e.message);
            } finally {
                deployScriptBtn.disabled = false;
                deployScriptBtn.textContent = "Deploy Remote Script";
            }
        }
    });
}

// Close modal when clicking outside the card
settingsModal.addEventListener('click', (e) => {
    if (e.target === settingsModal) {
        settingsModal.classList.add('hidden');
    }
});

function showThinking() {
    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'message ai';
    thinkingDiv.id = 'thinking-indicator';
    
    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'bubble';
    
    const details = document.createElement('details');
    details.className = 'status-container';
    details.open = true;
    
    const summary = document.createElement('summary');
    summary.textContent = 'Execution Trace...';
    
    const statusContent = document.createElement('div');
    statusContent.className = 'status-content';
    
    details.appendChild(summary);
    details.appendChild(statusContent);
    bubbleDiv.appendChild(details);
    
    thinkingDiv.appendChild(bubbleDiv);
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
 * Auto-saves the current session state to the backend.
 */
async function autoSaveSession() {
    if (!chatHistoryArray.length || !window.api || !window.api.sessions) return;
    try {
        const payload = {
            id: currentSessionId,
            title: currentSessionTitle,
            genre: currentSessionGenre,
            chat_history: chatHistoryArray,
            metrics: {
                cost_flash: costFlash,
                cost_pro: costPro
            }
        };
        const result = await window.api.sessions.save(backendUrl, payload);
        if (result && result.session) {
            currentSessionId = result.session.id;
            currentSessionTitle = result.session.title;
        }
    } catch (e) {
        console.warn("Failed to auto-save session:", e);
    }
}

/**
 * Handles sending a message.
 */
async function handleSendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    // 1. Append user message
    const instruction = currentSessionGenre ? `[Style: ${currentSessionGenre}] ${text}` : text;
    appendMessage('user', text);
    chatHistoryArray.push({ role: "user", content: instruction });
    await autoSaveSession();
    
    // 2. Clear and disable input
    chatInput.value = '';
    chatInput.style.height = 'auto';
    chatInput.style.overflowY = 'hidden';
    chatInput.disabled = true;
    sendBtn.disabled = true;
    
    // 3. Show thinking indicator
    showThinking();

    // Inject Visual Anchor into Log Drawer
    if (logContent) {
        const anchor = document.createElement('div');
        anchor.className = 'log-entry system';
        anchor.style.fontWeight = 'bold';
        anchor.style.color = 'var(--accent-color)';
        anchor.textContent = `\n--- [PROMPT SENT: ${new Date().toLocaleTimeString()}] ---`;
        logContent.appendChild(anchor);
        logContent.scrollTop = logContent.scrollHeight;
    }

    try {
        // 4. Call API with configured backendUrl and stream callback
        const data = await window.api.sendChatMessage(text, backendUrl, chatHistoryArray, requireApproval, (chunk) => {
            if (chunk.type === 'status') {
                const statusContent = document.querySelector('#thinking-indicator .status-content');
                if (statusContent) {
                    const entry = document.createElement('div');
                    entry.className = 'status-update';
                    entry.textContent = chunk.message;
                    statusContent.appendChild(entry);
                    chatHistory.scrollTop = chatHistory.scrollHeight;
                }
            } else if (chunk.type === 'debug') {
                console.log('%c[DEBUG] \n' + chunk.content, 'color: #00FF00; font-family: monospace; background: #111; padding: 4px;');
            } else if (chunk.type === 'warning') {
                const warningDiv = document.createElement('div');
                warningDiv.style.color = '#ffb74d';
                warningDiv.style.fontSize = '0.85em';
                warningDiv.style.fontStyle = 'italic';
                warningDiv.style.margin = '4px 0 8px 12px';
                warningDiv.style.opacity = '0.8';
                warningDiv.textContent = `⚠️ Warning: ${chunk.message}`;
                chatHistory.appendChild(warningDiv);
                chatHistory.scrollTop = chatHistory.scrollHeight;
            } else if (chunk.type === 'approval_required') {
                const indicator = document.getElementById('thinking-indicator');
                if (indicator) {
                    const bubble = indicator.querySelector('.bubble');
                    const cardDiv = document.createElement('div');
                    cardDiv.className = 'approval-card';
                    
                    let actionsHtml = '<h4>Pending Actions:</h4><ul>';
                    chunk.actions.forEach(action => {
                        actionsHtml += `<li><span class="tool-name">${action.tool}</span><br><span class="tool-args">${JSON.stringify(action.args)}</span></li>`;
                    });
                    actionsHtml += '</ul>';
                    
                    cardDiv.innerHTML = actionsHtml;
                    
                    const btnContainer = document.createElement('div');
                    btnContainer.className = 'actions';
                    
                    const cancelBtn = document.createElement('button');
                    cancelBtn.className = 'secondary-btn';
                    cancelBtn.textContent = 'Cancel';
                    
                    const approveBtn = document.createElement('button');
                    approveBtn.className = 'primary-btn';
                    approveBtn.textContent = 'Approve';
                    
                    btnContainer.appendChild(cancelBtn);
                    btnContainer.appendChild(approveBtn);
                    cardDiv.appendChild(btnContainer);
                    
                    bubble.appendChild(cardDiv);
                    
                    const respond = async (approved) => {
                        cancelBtn.disabled = true;
                        approveBtn.disabled = true;
                        try {
                            await fetch(`${backendUrl}/api/action-response`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ approved })
                            });
                            
                            cardDiv.className = 'approval-card collapsed';
                            cardDiv.style = ''; // Reset any inline styles
                            
                            const details = document.createElement('details');
                            details.className = 'approval-details';
                            
                            const summary = document.createElement('summary');
                            if (approved) {
                                summary.innerHTML = '<span style="color: var(--success-color);">✓ Actions Approved</span>';
                            } else {
                                summary.innerHTML = '<span style="color: var(--text-secondary);">✗ Actions Canceled</span>';
                            }
                            
                            const listDiv = document.createElement('div');
                            listDiv.className = 'approval-list-content';
                            listDiv.innerHTML = actionsHtml;
                            
                            details.appendChild(summary);
                            details.appendChild(listDiv);
                            
                            cardDiv.innerHTML = '';
                            cardDiv.appendChild(details);
                        } catch (e) {
                            console.error('Failed to send approval:', e);
                        }
                    };
                    
                    cancelBtn.addEventListener('click', () => respond(false));
                    approveBtn.addEventListener('click', () => respond(true));
                    
                    chatHistory.scrollTop = chatHistory.scrollHeight;
                }
            }
        });
        
        // 5. Success
        const indicator = document.getElementById('thinking-indicator');
        if (indicator) {
            indicator.removeAttribute('id');
            const details = indicator.querySelector('.status-container');
            if (details) {
                details.removeAttribute('open');
            }
            
            const finalContent = document.createElement('div');
            finalContent.className = 'final-content';
            finalContent.innerHTML = marked.parse(data.response || "I couldn't process that request.");
            indicator.querySelector('.bubble').appendChild(finalContent);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        } else {
            appendMessage('ai', data.response || "I couldn't process that request.");
        }
        
        chatHistoryArray.push({ role: "assistant", content: data.response || "" });
        
        // Calculate cost
        if (data.pro_input_tokens !== undefined && data.pro_output_tokens !== undefined) {
            const proIn = data.pro_input_tokens;
            const proOut = data.pro_output_tokens;
            if (proIn > 0 || proOut > 0) {
                const stepCostPro = (proIn / 1000000) * 2.00 + (proOut / 1000000) * 12.00;
                costPro += stepCostPro;
                proTokens += (proIn + proOut);
                if (costPromptProM) costPromptProM.textContent = `Pro: $${stepCostPro.toFixed(4)}`;
                costProM.textContent = `Pro: $${costPro.toFixed(4)}`;
                
                historyProCost += stepCostPro;
                localStorage.setItem('historyProCost', historyProCost.toString());
                historyProM.textContent = `Pro: $${historyProCost.toFixed(4)}`;
            }
        }
        
        if (data.flash_input_tokens !== undefined && data.flash_output_tokens !== undefined) {
            const flashIn = data.flash_input_tokens;
            const flashOut = data.flash_output_tokens;
            if (flashIn > 0 || flashOut > 0) {
                const stepCostFlash = (flashIn / 1000000) * 0.25 + (flashOut / 1000000) * 1.50;
                costFlash += stepCostFlash;
                flashTokens += (flashIn + flashOut);
                if (costPromptFlashM) costPromptFlashM.textContent = `Flash: $${stepCostFlash.toFixed(4)}`;
                costFlashM.textContent = `Flash: $${costFlash.toFixed(4)}`;
                
                historyFlashCost += stepCostFlash;
                localStorage.setItem('historyFlashCost', historyFlashCost.toString());
                historyFlashM.textContent = `Flash: $${historyFlashCost.toFixed(4)}`;
            }
        }
        
        // Backwards compatibility for old payload structure
        if (data.model_used && data.input_tokens !== undefined && data.output_tokens !== undefined && data.pro_input_tokens === undefined) {
            const totalTokens = data.input_tokens + data.output_tokens;
            if (data.model_used.toUpperCase().includes('PRO')) {
                let stepCost = (data.input_tokens / 1000000) * 2.00 + (data.output_tokens / 1000000) * 12.00;
                costPro += stepCost;
                proTokens += totalTokens;
                costProM.textContent = `Pro: $${costPro.toFixed(4)} (${proTokens} tk)`;
                historyProCost += stepCost;
                localStorage.setItem('historyProCost', historyProCost.toString());
                historyProM.textContent = `Pro: $${historyProCost.toFixed(4)}`;
            } else if (data.model_used.toUpperCase().includes('FLASH')) {
                let stepCost = (data.input_tokens / 1000000) * 0.25 + (data.output_tokens / 1000000) * 1.50;
                costFlash += stepCost;
                flashTokens += totalTokens;
                costFlashM.textContent = `Flash: $${costFlash.toFixed(4)} (${flashTokens} tk)`;
                historyFlashCost += stepCost;
                localStorage.setItem('historyFlashCost', historyFlashCost.toString());
                historyFlashM.textContent = `Flash: $${historyFlashCost.toFixed(4)}`;
            }
        }

        await autoSaveSession();
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
        statusIndicator.innerHTML = '<span class="status-dot" style="background-color: var(--accent-color);"></span> Backend Ready';
        statusIndicator.className = 'status-ready';
        fetchSessionContext();
    } else {
        statusIndicator.innerHTML = '<span class="status-dot" style="background-color: var(--error-color);"></span> Backend Offline';
        statusIndicator.className = 'status-offline';
    }
}

async function fetchSessionContext() {
    try {
        const response = await fetch(`${backendUrl}/api/session-context`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const result = await response.json();
        
        if (result.status === 'error') {
            throw new Error(result.message);
        }
        
        const data = result.data || result;
        
        const bpm = data.tempo ? Math.round(data.tempo) : '--';
        
        const noteNames = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
        let key = '--';
        if (data.root_note !== undefined && data.root_note >= 0 && data.root_note <= 11 && data.scale_name) {
            key = `${noteNames[data.root_note]} ${data.scale_name}`;
        } else if (data.scale_name && data.scale_name !== "Unknown") {
            key = data.scale_name;
        }
        
        let tracksCount = '--';
        if (data.tracks) {
            tracksCount = Array.isArray(data.tracks) ? data.tracks.length : data.tracks;
        }

        inspectorBpm.textContent = `BPM: ${bpm}`;
        inspectorKey.textContent = `Key: ${key}`;
        inspectorTracks.textContent = `Tracks: ${tracksCount}`;
    } catch (error) {
        console.warn("Failed to fetch session context:", error);
        inspectorBpm.textContent = `BPM: --`;
        inspectorKey.textContent = `Key: --`;
        inspectorTracks.textContent = `Tracks: --`;
    }
}

if (refreshSessionBtn) {
    refreshSessionBtn.addEventListener('click', fetchSessionContext);
}

async function checkConnection() {
    try {
        await fetch(`${backendUrl}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ gemini_api_key: geminiApiKey, mcp_port: mcpPort })
        }).catch(e => console.warn("Could not sync initial settings to backend", e));

        await window.api.ping(backendUrl);
        updateStatus(true);
    } catch (error) {
        updateStatus(false);
    }
}

// Event Listeners
sendBtn.addEventListener('click', handleSendMessage);

chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
    }
});

chatInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = this.scrollHeight + 'px';
    if (this.scrollHeight > 200) {
        this.style.overflowY = 'auto';
    } else {
        this.style.overflowY = 'hidden';
    }
});

chatInput.addEventListener('paste', function(e) {
    e.preventDefault();
    const text = (e.clipboardData || window.clipboardData).getData('text/plain');
    const start = this.selectionStart;
    const end = this.selectionEnd;
    const value = this.value;
    this.value = value.substring(0, start) + text + value.substring(end);
    this.selectionStart = this.selectionEnd = start + text.length;
    this.dispatchEvent(new Event('input'));
});

// Log Viewer DOM & Logic
const logDrawer = document.getElementById('log-drawer');
const logContent = document.getElementById('log-content');
const toggleLogsBtn = document.getElementById('toggle-logs-btn');

if (toggleLogsBtn) {
    toggleLogsBtn.addEventListener('click', () => {
        logDrawer.classList.toggle('hidden');
        if (logDrawer.classList.contains('hidden')) {
            toggleLogsBtn.textContent = 'Show Logs';
        } else {
            toggleLogsBtn.textContent = 'Hide Logs';
            logContent.scrollTop = logContent.scrollHeight;
        }
    });
}

if (window.api && window.api.onBackendLog) {
    window.api.onBackendLog((data) => {
        const logLine = document.createElement('div');
        logLine.className = `log-entry ${data.type || 'info'}`;
        // Strip terminal color codes
        let cleanMsg = typeof data === 'string' ? data : data.message;
        cleanMsg = cleanMsg.replace(/[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g, '');
        
        logLine.textContent = cleanMsg;
        const logsOutput = document.getElementById('log-content');
        if (logsOutput) {
            logsOutput.appendChild(logLine);
            if (logsOutput.childNodes.length > 500) {
                logsOutput.removeChild(logsOutput.firstChild);
            }
            logsOutput.scrollTop = logsOutput.scrollHeight;
        }
    });
}

// INITIALIZATION
window.addEventListener('DOMContentLoaded', () => {
    checkConnection();
    chatInput.focus();
    loadHistoryList(); // Load history on startup
});

// --- Session History Interaction Logic ---

let sessionToDelete = null;
const deleteConfirmModal = document.getElementById('delete-confirm-modal');
const deleteConfirmYesBtn = document.getElementById('delete-confirm-yes-btn');
const deleteConfirmNoBtn = document.getElementById('delete-confirm-no-btn');

deleteConfirmNoBtn.addEventListener('click', () => {
    deleteConfirmModal.classList.add('hidden');
    sessionToDelete = null;
});

deleteConfirmYesBtn.addEventListener('click', async () => {
    if (sessionToDelete) {
        try {
            await window.api.sessions.delete(backendUrl, sessionToDelete);
            if (currentSessionId === sessionToDelete) {
                clearBtn.click();
            }
            await loadHistoryList();
        } catch (e) {
            console.error("Failed to delete session", e);
        }
        deleteConfirmModal.classList.add('hidden');
        sessionToDelete = null;
    }
});

async function loadHistoryList() {
    if (!window.api || !window.api.sessions) return;
    try {
        const sessions = await window.api.sessions.getAll(backendUrl);
        sessions.sort((a, b) => b.last_edited - a.last_edited);
        
        historyList.innerHTML = '';
        
        if (sessions.length === 0) {
            historyList.innerHTML = '<div style="color: var(--text-secondary); text-align: center; padding: 2rem;">No history yet.</div>';
            return;
        }

        sessions.forEach(session => {
            const item = document.createElement('div');
            item.className = 'history-item' + (currentSessionId === session.id ? ' active' : '');
            
            const date = new Date(session.last_edited * 1000).toLocaleString();
            
            item.innerHTML = `
                <div class="history-item-content">
                    <div class="history-item-title">${session.title}</div>
                    <div class="history-item-date">${date}</div>
                </div>
                <button class="history-item-menu-btn">⋮</button>
                <div class="history-item-menu hidden">
                    <button class="rename-btn">Rename</button>
                    <button class="delete-btn">Delete</button>
                </div>
            `;
            
            item.querySelector('.history-item-content').addEventListener('click', () => {
                loadSession(session.id);
            });
            
            const menuBtn = item.querySelector('.history-item-menu-btn');
            const menu = item.querySelector('.history-item-menu');
            
            menuBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                document.querySelectorAll('.history-item-menu').forEach(m => {
                    if (m !== menu) m.classList.add('hidden');
                });
                menu.classList.toggle('hidden');
            });
            
            item.querySelector('.rename-btn').addEventListener('click', async (e) => {
                e.stopPropagation();
                menu.classList.add('hidden');
                const newTitle = prompt("Enter new session title:", session.title);
                if (newTitle && newTitle.trim() !== "") {
                    try {
                        const fullSession = await window.api.sessions.getOne(backendUrl, session.id);
                        fullSession.title = newTitle.trim();
                        await window.api.sessions.save(backendUrl, fullSession);
                        if (currentSessionId === session.id) {
                            currentSessionTitle = fullSession.title;
                        }
                        loadHistoryList();
                    } catch (err) {
                        console.error("Rename failed", err);
                    }
                }
            });
            
            item.querySelector('.delete-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                menu.classList.add('hidden');
                sessionToDelete = session.id;
                deleteConfirmModal.classList.remove('hidden');
            });

            historyList.appendChild(item);
        });
    } catch (e) {
        console.error("Failed to load history list:", e);
    }
}

document.addEventListener('click', (e) => {
    if (!e.target.closest('.history-item-menu-btn')) {
        document.querySelectorAll('.history-item-menu').forEach(m => m.classList.add('hidden'));
    }
});

async function loadSession(id) {
    if (!window.api || !window.api.sessions) return;
    try {
        const session = await window.api.sessions.getOne(backendUrl, id);
        currentSessionId = session.id;
        currentSessionTitle = session.title;
        currentSessionGenre = session.genre || '';
        if (sessionGenreInput) sessionGenreInput.value = currentSessionGenre;
        chatHistoryArray = session.chat_history || [];
        
        costFlash = session.metrics?.cost_flash || 0.0;
        costPro = session.metrics?.cost_pro || 0.0;
        if (costPromptFlashM) costPromptFlashM.textContent = `Flash: $0.0000`;
        if (costPromptProM) costPromptProM.textContent = `Pro: $0.0000`;
        if (costFlashM) costFlashM.textContent = `Flash: $${costFlash.toFixed(4)}`;
        if (costProM) costProM.textContent = `Pro: $${costPro.toFixed(4)}`;
        
        chatHistory.innerHTML = '';
        chatHistoryArray.forEach(msg => {
            let displayRole = msg.role === "assistant" ? "ai" : "user";
            appendMessage(displayRole, msg.content);
        });
        
        historyDrawer.classList.add('closed');
        document.body.classList.remove('drawer-open');
        
        loadHistoryList();
    } catch (e) {
        console.error("Failed to load session:", e);
        alert("Failed to load session. Check backend logs.");
    }
}

if (sessionGenreInput) {
    sessionGenreInput.addEventListener('change', () => {
        currentSessionGenre = sessionGenreInput.value.trim();
        autoSaveSession();
    });
}
