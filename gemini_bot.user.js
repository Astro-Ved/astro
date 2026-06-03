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
        captureEnabled: true,
        latencyMs: 500, // Delay between actions
        maxImageSize: 320 // Scale down canvas for low latency
    };

    // --- UI Setup ---
    function initUI() {
        const panel = document.createElement('div');
        panel.style.cssText = `
            position: fixed; top: 10px; right: 10px; width: 300px;
            background: rgba(0, 0, 0, 0.85); color: #00ff00;
            font-family: monospace; font-size: 12px; padding: 15px;
            border: 1px solid #00ff00; z-index: 999999; border-radius: 5px;
        `;

        panel.innerHTML = `
            <h3 style="margin: 0 0 10px 0; color: #fff;">🤖 Gemini Game Bot</h3>

            <label>API Key:</label><br>
            <input type="password" id="gemini-apikey" value="${STATE.apiKey}" style="width: 100%; margin-bottom: 10px; background: #222; color: #fff; border: 1px solid #555;">

            <label>Game Controls Prompt (Saved per site):</label><br>
            <textarea id="gemini-controls" style="width: 100%; height: 60px; margin-bottom: 10px; background: #222; color: #fff; border: 1px solid #555;">${STATE.controls}</textarea>

            <label>
                <input type="checkbox" id="gemini-capture" ${STATE.captureEnabled ? 'checked' : ''}> Enable Screen Capture (Vision)
            </label><br><br>

            <button id="gemini-save" style="background: #333; color: #fff; border: 1px solid #00ff00; padding: 5px; cursor: pointer; width: 100%; margin-bottom: 10px;">Save Settings</button>
            <button id="gemini-toggle" style="background: #004400; color: #00ff00; border: 1px solid #00ff00; padding: 10px; cursor: pointer; width: 100%; font-weight: bold;">START BOT</button>

            <div id="gemini-status" style="margin-top: 10px; color: #aaa; white-space: pre-wrap; font-size: 10px;">Status: Idle</div>
        `;

        document.body.appendChild(panel);

        document.getElementById('gemini-save').addEventListener('click', () => {
            STATE.apiKey = document.getElementById('gemini-apikey').value;
            STATE.controls = document.getElementById('gemini-controls').value;
            STATE.captureEnabled = document.getElementById('gemini-capture').checked;

            GM_setValue('gemini_api_key', STATE.apiKey);
            GM_setValue(`controls_${window.location.hostname}`, STATE.controls);
            updateStatus("Settings saved locally!");
        });

        document.getElementById('gemini-toggle').addEventListener('click', (e) => {
            STATE.isRunning = !STATE.isRunning;
            e.target.innerText = STATE.isRunning ? 'STOP BOT' : 'START BOT';
            e.target.style.background = STATE.isRunning ? '#440000' : '#004400';
            e.target.style.color = STATE.isRunning ? '#ff0000' : '#00ff00';

            if (STATE.isRunning) {
                updateStatus("Bot started...");
                gameLoop();
            } else {
                updateStatus("Bot stopped.");
            }
        });
    }

    function updateStatus(msg) {
        const statusEl = document.getElementById('gemini-status');
        if (statusEl) statusEl.innerText = `Status: ${msg}`;
    }

    // --- Screen Capture ---
    function captureGameState() {
        if (!STATE.captureEnabled) return null;

        // Try to find the game canvas
        const canvases = document.querySelectorAll('canvas');
        if (canvases.length === 0) return null;

        // Assume the largest canvas is the game
        let targetCanvas = canvases[0];
        let maxArea = targetCanvas.width * targetCanvas.height;
        for (let i = 1; i < canvases.length; i++) {
            let area = canvases[i].width * canvases[i].height;
            if (area > maxArea) {
                maxArea = area;
                targetCanvas = canvases[i];
            }
        }

        // Scale down for latency
        const offscreen = document.createElement('canvas');
        const scale = Math.min(STATE.maxImageSize / targetCanvas.width, STATE.maxImageSize / targetCanvas.height, 1);
        offscreen.width = targetCanvas.width * scale;
        offscreen.height = targetCanvas.height * scale;

        const ctx = offscreen.getContext('2d');
        ctx.drawImage(targetCanvas, 0, 0, offscreen.width, offscreen.height);

        // Return base64 without prefix
        const dataUrl = offscreen.toDataURL('image/jpeg', 0.5);
        return dataUrl.split(',')[1];
    }

    // --- Action Execution ---
    function executeActions(actionsText) {
        try {
            // Expecting Gemini to return a JSON array like: [{"type": "keydown", "key": "w"}, {"type": "mousedown", "button": 0}]
            // Extract JSON from potential markdown blocks
            const jsonMatch = actionsText.match(/\[.*\]/s) || actionsText.match(/\{.*\}/s);
            if (!jsonMatch) {
                updateStatus("No parseable JSON in response:\n" + actionsText.substring(0, 50));
                return;
            }

            let actions = JSON.parse(jsonMatch[0]);
            if (!Array.isArray(actions)) actions = [actions];

            updateStatus(`Executing ${actions.length} actions...`);

            const target = document.querySelectorAll('canvas')[0] || document.body;

            actions.forEach(action => {
                if (action.type === 'keydown' || action.type === 'keyup') {
                    const evt = new KeyboardEvent(action.type, {
                        key: action.key,
                        code: action.code || `Key${action.key.toUpperCase()}`,
                        keyCode: action.key.toUpperCase().charCodeAt(0),
                        bubbles: true,
                        cancelable: true
                    });
                    document.dispatchEvent(evt);
                } else if (action.type === 'mousedown' || action.type === 'mouseup' || action.type === 'click') {
                    const evt = new MouseEvent(action.type, {
                        button: action.button || 0,
                        clientX: action.x || window.innerWidth / 2,
                        clientY: action.y || window.innerHeight / 2,
                        bubbles: true,
                        cancelable: true
                    });
                    target.dispatchEvent(evt);
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

            const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${STATE.apiKey}`;

            const parts = [
                {
                    text: `You are an automated game-playing AI bot playing a game on a web browser.
Your goal is to analyze the screen and output commands to play the game optimally.
The user has mapped the following controls for this game: ${STATE.controls}

Output ONLY a raw JSON array of objects representing actions you want to take right now. Do not wrap in markdown tags.
Example format:
[
  {"type": "keydown", "key": "w"},
  {"type": "mousedown", "button": 0}
]

Analyze the screen state and make the best move. Keep it brief and output ONLY the JSON array.`
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
            const imgData = captureGameState();
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
        window.addEventListener('load', initUI);
    }

})();