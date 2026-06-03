// ==UserScript==
// @name         Gemini AI Game Automation Bot
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Automates web games using Gemini API decisions with vision support
// @match        *://*/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @connect      generativelanguage.googleapis.com
// ==/UserScript==

(function() {
    'use strict';

    // --- Configuration & State ---
    const STATE = {
        isRunning: false,
        isProcessing: false, // Prevent overlapping API calls
        apiKey: GM_getValue('gemini_api_key', ''),
        controls: GM_getValue(`controls_${window.location.hostname}`, 'W, A, S, D, Left Click'),
        captureEnabled: GM_getValue('gemini_capture', true),
        latencyMs: GM_getValue('gemini_latency', 500), // Delay between actions
        maxImageSize: GM_getValue('gemini_max_size', 320), // Scale down canvas for low latency
        model: GM_getValue('gemini_model', 'gemini-2.5-flash'), // Added model selection
        gameplayFeedback: GM_getValue('gemini_feedback', ''), // User feedback to improve gameplay
        menuVisible: true,
        videoElement: null, // For screen capture fallback
        virtualCursor: null // Virtual mouse pointer
    };

    // --- UI Setup ---
    function initUI() {
        // Create Virtual Cursor
        const cursor = document.createElement('div');
        cursor.id = 'gemini-virtual-cursor';
        cursor.style.cssText = `
            position: fixed; width: 15px; height: 15px;
            background-color: red; border-radius: 50%;
            border: 2px solid white; z-index: 9999999;
            pointer-events: none; /* Let clicks pass through to game */
            transform: translate(-50%, -50%);
            display: none;
            box-shadow: 0 0 5px rgba(0,0,0,0.5);
        `;
        document.body.appendChild(cursor);
        STATE.virtualCursor = cursor;

        const panel = document.createElement('div');
        panel.id = 'gemini-bot-panel';
        panel.style.cssText = `
            position: fixed; top: 10px; right: 10px; width: 300px;
            background: rgba(0, 0, 0, 0.85); color: #00ff00;
            font-family: monospace; font-size: 12px; padding: 15px;
            border: 1px solid #00ff00; z-index: 999999; border-radius: 5px;
        `;

        panel.innerHTML = `
            <h3 style="margin: 0 0 10px 0; color: #fff;">🤖 Gemini Game Bot <span style="font-size:10px;color:#aaa;">(Toggle: Insert)</span></h3>

            <label>API Key:</label><br>
            <input type="password" id="gemini-apikey" value="${STATE.apiKey}" style="width: 100%; margin-bottom: 10px; background: #222; color: #fff; border: 1px solid #555;">

            <label>Model:</label><br>
            <select id="gemini-model" style="width: 100%; margin-bottom: 10px; background: #222; color: #fff; border: 1px solid #555;">
                <option value="gemini-2.5-flash" ${STATE.model === 'gemini-2.5-flash' ? 'selected' : ''}>Gemini 2.5 Flash</option>
                <option value="gemini-2.5-pro" ${STATE.model === 'gemini-2.5-pro' ? 'selected' : ''}>Gemini 2.5 Pro</option>
                <option value="gemini-1.5-flash" ${STATE.model === 'gemini-1.5-flash' ? 'selected' : ''}>Gemini 1.5 Flash</option>
            </select><br>

            <label>Game Controls Prompt (Saved per site):</label><br>
            <textarea id="gemini-controls" style="width: 100%; height: 60px; margin-bottom: 10px; background: #222; color: #fff; border: 1px solid #555;">${STATE.controls}</textarea>

            <label>Gameplay Feedback/Hints (Real-time hints to the AI):</label><br>
            <textarea id="gemini-feedback" style="width: 100%; height: 40px; margin-bottom: 10px; background: #222; color: #fff; border: 1px solid #555;" placeholder="e.g., Focus on headshots, dodge left...">${STATE.gameplayFeedback}</textarea>

            <label>
                <input type="checkbox" id="gemini-capture" ${STATE.captureEnabled ? 'checked' : ''}> Enable Screen Capture (Vision)
            </label><br>

            <label style="display:inline-block; margin-top:10px; width:50%;">Latency (ms):<br>
                <input type="number" id="gemini-latency" value="${STATE.latencyMs}" style="width: 90%; background: #222; color: #fff; border: 1px solid #555;">
            </label>
            <label style="display:inline-block; margin-top:10px; width:45%;">Max Res (px):<br>
                <input type="number" id="gemini-max-size" value="${STATE.maxImageSize}" style="width: 100%; background: #222; color: #fff; border: 1px solid #555;">
            </label><br><br>

            <button id="gemini-save" style="background: #333; color: #fff; border: 1px solid #00ff00; padding: 5px; cursor: pointer; width: 100%; margin-bottom: 10px;">Save Settings</button>
            <button id="gemini-toggle" style="background: #004400; color: #00ff00; border: 1px solid #00ff00; padding: 10px; cursor: pointer; width: 100%; font-weight: bold;">START BOT</button>

            <div id="gemini-status" style="margin-top: 10px; color: #aaa; white-space: pre-wrap; font-size: 10px;">Status: Idle</div>
        `;

        document.body.appendChild(panel);

        // Toggle menu with Insert key
        window.addEventListener('keydown', (e) => {
            if (e.code === 'Insert') {
                STATE.menuVisible = !STATE.menuVisible;
                panel.style.display = STATE.menuVisible ? 'block' : 'none';
            }
        });

        document.getElementById('gemini-save').addEventListener('click', () => {
            STATE.apiKey = document.getElementById('gemini-apikey').value;
            STATE.model = document.getElementById('gemini-model').value;
            STATE.controls = document.getElementById('gemini-controls').value;
            STATE.gameplayFeedback = document.getElementById('gemini-feedback').value;
            STATE.captureEnabled = document.getElementById('gemini-capture').checked;
            STATE.latencyMs = parseInt(document.getElementById('gemini-latency').value, 10) || 500;
            STATE.maxImageSize = parseInt(document.getElementById('gemini-max-size').value, 10) || 320;

            GM_setValue('gemini_api_key', STATE.apiKey);
            GM_setValue('gemini_model', STATE.model);
            GM_setValue(`controls_${window.location.hostname}`, STATE.controls);
            GM_setValue('gemini_feedback', STATE.gameplayFeedback);
            GM_setValue('gemini_capture', STATE.captureEnabled);
            GM_setValue('gemini_latency', STATE.latencyMs);
            GM_setValue('gemini_max_size', STATE.maxImageSize);

            updateStatus("Settings saved locally!");
        });

        document.getElementById('gemini-toggle').addEventListener('click', async (e) => {
            STATE.isRunning = !STATE.isRunning;
            e.target.innerText = STATE.isRunning ? 'STOP BOT' : 'START BOT';
            e.target.style.background = STATE.isRunning ? '#440000' : '#004400';
            e.target.style.color = STATE.isRunning ? '#ff0000' : '#00ff00';

            if (STATE.isRunning) {
                if (STATE.captureEnabled && !STATE.videoElement) {
                    updateStatus("Requesting screen capture...");
                    const success = await initScreenCapture();
                    if (!success) {
                        STATE.isRunning = false;
                        e.target.innerText = 'START BOT';
                        e.target.style.background = '#004400';
                        e.target.style.color = '#00ff00';
                        return;
                    }
                }
                if (STATE.virtualCursor) STATE.virtualCursor.style.display = 'block';
                updateStatus("Bot started...");
                gameLoop();
            } else {
                if (STATE.virtualCursor) STATE.virtualCursor.style.display = 'none';
                updateStatus("Bot stopped.");
            }
        });
    }

    function updateStatus(msg) {
        const statusEl = document.getElementById('gemini-status');
        if (statusEl) statusEl.innerText = `Status: ${msg}`;
    }

    // --- Screen Capture ---
    async function initScreenCapture() {
        if (STATE.videoElement) return true; // Already initialized
        try {
            const stream = await navigator.mediaDevices.getDisplayMedia({
                video: { cursor: "never" },
                audio: false
            });
            STATE.videoElement = document.createElement('video');
            STATE.videoElement.srcObject = stream;
            STATE.videoElement.play();
            return new Promise((resolve) => {
                STATE.videoElement.onloadedmetadata = () => resolve(true);
            });
        } catch (err) {
            updateStatus("Screen capture permission denied.");
            console.error("Screen capture failed:", err);
            return false;
        }
    }

    async function captureGameState() {
        if (!STATE.captureEnabled) return null;

        let sourceNode = null;

        // Use video capture as primary if available (bypasses WebGL canvas tainting)
        if (STATE.videoElement && STATE.videoElement.readyState >= 2) {
            sourceNode = STATE.videoElement;
        } else {
            // Fallback to searching for canvas
            const canvases = document.querySelectorAll('canvas');
            if (canvases.length > 0) {
                let targetCanvas = canvases[0];
                let maxArea = targetCanvas.width * targetCanvas.height;
                for (let i = 1; i < canvases.length; i++) {
                    let area = canvases[i].width * canvases[i].height;
                    if (area > maxArea) {
                        maxArea = area;
                        targetCanvas = canvases[i];
                    }
                }
                sourceNode = targetCanvas;
            }
        }

        if (!sourceNode) return null;

        // Scale down for latency
        const offscreen = document.createElement('canvas');
        const srcWidth = sourceNode.videoWidth || sourceNode.width;
        const srcHeight = sourceNode.videoHeight || sourceNode.height;

        if (!srcWidth || !srcHeight) return null;

        const scale = Math.min(STATE.maxImageSize / srcWidth, STATE.maxImageSize / srcHeight, 1);
        offscreen.width = srcWidth * scale;
        offscreen.height = srcHeight * scale;

        const ctx = offscreen.getContext('2d');
        try {
            ctx.drawImage(sourceNode, 0, 0, offscreen.width, offscreen.height);
            // Return base64 without prefix
            const dataUrl = offscreen.toDataURL('image/jpeg', 0.5);
            return dataUrl.split(',')[1];
        } catch (e) {
            // Tainted canvas! We need screen capture.
            if (!STATE.videoElement) {
                updateStatus("Canvas tainted! Please click START BOT again to grant screen capture permission.");
                STATE.isRunning = false;
                document.getElementById('gemini-toggle').innerText = 'START BOT';
                document.getElementById('gemini-toggle').style.background = '#004400';
                document.getElementById('gemini-toggle').style.color = '#00ff00';
            }
            throw e;
        }
    }

    // --- Action Execution ---
    function executeActions(actionsText) {
        try {
            // Expecting format like: ["PRESS: w", "MOUSE: 500, 300"]
            const jsonMatch = actionsText.match(/\[.*\]/s) || actionsText.match(/\{.*\}/s);
            if (!jsonMatch) {
                updateStatus("No parseable JSON in response:\n" + actionsText.substring(0, 50));
                return;
            }

            let actions = JSON.parse(jsonMatch[0]);
            if (!Array.isArray(actions)) actions = [actions];

            updateStatus(`Executing ${actions.length} actions...`);

            const target = document.querySelectorAll('canvas')[0] || document.body;

            actions.forEach(actionStr => {
                if (typeof actionStr !== 'string') return;

                if (actionStr.startsWith('PRESS:')) {
                    const keyVal = actionStr.split(':')[1].trim();
                    const upperKey = keyVal.toUpperCase();

                    // Simulate Keydown
                    document.dispatchEvent(new KeyboardEvent('keydown', {
                        key: keyVal,
                        code: `Key${upperKey}`,
                        keyCode: upperKey.charCodeAt(0) || 0,
                        bubbles: true, cancelable: true
                    }));

                    // Simulate Keyup after slight delay
                    setTimeout(() => {
                        document.dispatchEvent(new KeyboardEvent('keyup', {
                            key: keyVal,
                            code: `Key${upperKey}`,
                            keyCode: upperKey.charCodeAt(0) || 0,
                            bubbles: true, cancelable: true
                        }));
                    }, 50);

                } else if (actionStr.startsWith('MOUSE:')) {
                    const coords = actionStr.split(':')[1].split(',');
                    const x = parseInt(coords[0].trim());
                    const y = parseInt(coords[1].trim());

                    if (!isNaN(x) && !isNaN(y)) {
                        // Move Virtual Cursor
                        if (STATE.virtualCursor) {
                            STATE.virtualCursor.style.left = `${x}px`;
                            STATE.virtualCursor.style.top = `${y}px`;
                        }

                        // Dispatch Mouse events at coordinates
                        const evtInit = {
                            clientX: x, clientY: y,
                            bubbles: true, cancelable: true,
                            view: window
                        };
                        target.dispatchEvent(new MouseEvent('mousemove', evtInit));
                        target.dispatchEvent(new MouseEvent('mousedown', Object.assign({button: 0}, evtInit)));
                        setTimeout(() => {
                            target.dispatchEvent(new MouseEvent('mouseup', Object.assign({button: 0}, evtInit)));
                            target.dispatchEvent(new MouseEvent('click', Object.assign({button: 0}, evtInit)));
                        }, 50);
                    }
                }
            });

        } catch (e) {
            updateStatus("Error parsing actions: " + e.message);
            console.error("Action parse error:", e, actionsText);
        }
    }

    // --- API Communication ---
    function callGeminiAPI(base64Image) {
        return new Promise((resolve, reject) => {
            if (!STATE.apiKey) {
                reject("API Key missing!");
                return;
            }

            const url = `https://generativelanguage.googleapis.com/v1beta/models/${STATE.model}:generateContent?key=${STATE.apiKey}`;

            let promptText = `You are an automated game-playing AI bot playing a game on a web browser.
Your goal is to analyze the screen and output commands to play the game optimally.
The user has mapped the following controls for this game: ${STATE.controls}

Output ONLY a raw JSON array of strings representing actions you want to take right now. Do not wrap in markdown tags.
To press a key, use the format: "PRESS: key_name"
To click the mouse at a specific screen coordinate, use the format: "MOUSE: x, y"

Example format:
[
  "PRESS: w",
  "MOUSE: 500, 300"
]`;

            if (STATE.gameplayFeedback.trim() !== '') {
                promptText += `\n\nUSER GAMEPLAY FEEDBACK/HINTS (Prioritize these instructions): ${STATE.gameplayFeedback}`;
            }

            promptText += `\n\nAnalyze the screen state and make the best move. Keep it brief and output ONLY the JSON array.`;

            const parts = [
                {
                    text: promptText
                }
            ];

            if (base64Image) {
                parts.push({
                    inline_data: {
                        mime_type: "image/jpeg",
                        data: base64Image
                    }
                });
            }

            const payload = {
                contents: [{ parts: parts }],
                generationConfig: {
                    temperature: 0.1, // Low temp for more consistent/logical outputs
                    response_mime_type: "application/json"
                }
            };

            GM_xmlhttpRequest({
                method: "POST",
                url: url,
                headers: {
                    "Content-Type": "application/json"
                },
                data: JSON.stringify(payload),
                onload: function(response) {
                    if (response.status === 200) {
                        try {
                            const resJson = JSON.parse(response.responseText);
                            const text = resJson.candidates[0].content.parts[0].text;
                            resolve(text);
                        } catch (e) {
                            reject("Failed to parse Gemini response: " + e.message);
                        }
                    } else {
                        reject(`API Error ${response.status}: ${response.responseText}`);
                    }
                },
                onerror: function(err) {
                    reject("Network Error: " + err);
                }
            });
        });
    }

    // --- Game Loop ---
    async function gameLoop() {
        if (!STATE.isRunning) return;
        if (STATE.isProcessing) {
            // wait and try again
            setTimeout(gameLoop, 100);
            return;
        }

        STATE.isProcessing = true;
        updateStatus("Capturing screen...");

        try {
            const imgData = await captureGameState();
            updateStatus("Asking Gemini...");

            const start = performance.now();
            const aiResponse = await callGeminiAPI(imgData);
            const latency = performance.now() - start;

            updateStatus(`Received response (${Math.round(latency)}ms). Executing...`);
            executeActions(aiResponse);

        } catch (e) {
            updateStatus("Error: " + e);
            console.error(e);
        } finally {
            STATE.isProcessing = false;
            if (STATE.isRunning) {
                // Throttle based on requested latency
                setTimeout(gameLoop, STATE.latencyMs);
            }
        }
    }

    // Initialize
    if (typeof window !== 'undefined') {
        if (document.readyState === 'complete' || document.readyState === 'interactive') {
            initUI();
        } else {
            window.addEventListener('DOMContentLoaded', initUI);
        }
    }

})();