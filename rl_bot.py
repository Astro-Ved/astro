import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import os
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import random
from collections import deque
from playwright.sync_api import sync_playwright
import urllib.request

# URL for a hypothetical pretrained reward model (using a placeholder domain for demonstration)
MODEL_URL = "https://example.com/models/reward_model_v1.pth"
MODEL_FILE = "reward_model.pth"

class RewardModel(nn.Module):
    """A lightweight CNN to determine if the game is over or a score happened."""
    def __init__(self, input_channels):
        super(RewardModel, self).__init__()
        self.conv1 = nn.Conv2d(input_channels, 8, kernel_size=8, stride=4)
        self.conv2 = nn.Conv2d(8, 16, kernel_size=4, stride=2)
        # Output: [reward_value, done_prob]
        self.fc = nn.Linear(16 * 9 * 9, 2)

    def forward(self, x):
        x = torch.relu(self.conv1(x))
        x = torch.relu(self.conv2(x))
        x = x.view(x.size(0), -1)
        out = self.fc(x)
        # out[:, 0] = continuous/discrete reward
        # out[:, 1] = probability of 'done' (sigmoid)
        reward = out[:, 0]
        done_prob = torch.sigmoid(out[:, 1])
        return reward, done_prob

class SimpleDQN(nn.Module):
    """A very lightweight CNN for a potato PC."""
    def __init__(self, input_channels, num_actions):
        super(SimpleDQN, self).__init__()
        self.conv1 = nn.Conv2d(input_channels, 16, kernel_size=8, stride=4)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=4, stride=2)
        self.fc1 = nn.Linear(32 * 9 * 9, 256)
        self.fc2 = nn.Linear(256, num_actions)

    def forward(self, x):
        x = torch.relu(self.conv1(x))
        x = torch.relu(self.conv2(x))
        x = x.view(x.size(0), -1)
        x = torch.relu(self.fc1(x))
        return self.fc2(x)

class ReplayBuffer:
    def __init__(self, capacity=10000):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        state, action, reward, next_state, done = zip(*random.sample(self.buffer, batch_size))
        return np.array(state), action, reward, np.array(next_state), done

    def __len__(self):
        return len(self.buffer)

def capture_page(page, resize_dim=(84, 84)):
    """Captures the target Playwright page, converts to grayscale and resizes for potato PC."""
    try:
        screenshot_bytes = page.screenshot()
        # Convert bytes to numpy array
        nparr = np.frombuffer(screenshot_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return None

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Resize to smaller dimensions
        resized = cv2.resize(gray, resize_dim, interpolation=cv2.INTER_AREA)

        return resized
    except Exception as e:
        print(f"Error capturing page: {e}")
        return None

import threading
import time

# Example action space: Up, Down, Left, Right, None, plus mouse movements
ACTIONS = [
    'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space',
    'mouse_up', 'mouse_down', 'mouse_left', 'mouse_right', 'click'
]

def perform_action(page, action_idx):
    if action_idx >= len(ACTIONS):
        return

    action = ACTIONS[action_idx]

    if action.startswith('Arrow') or action == 'Space':
        page.keyboard.press(action)
    elif action.startswith('mouse_'):
        # In a real setup, you might want to track current coordinates and move relative to them.
        # This is a simplified example of jumping to predefined zones or moving relative.
        # Here we just execute a dummy relative move by getting the bounding box or center.
        # Since we don't track absolute state easily here, let's do small relative moves from center.

        viewport = page.viewport_size
        if not viewport:
            viewport = {'width': 800, 'height': 600}

        # Get current mouse position conceptually (Playwright doesn't expose it directly)
        # So we just do a click in center to ensure focus, then use a standard offset.
        # A more complex bot would store its x,y. We'll store it in the page object dynamically.
        if not hasattr(page, 'bot_mouse_x'):
            page.bot_mouse_x = viewport['width'] / 2
            page.bot_mouse_y = viewport['height'] / 2

        step = 50
        if action == 'mouse_up':
            page.bot_mouse_y = max(0, page.bot_mouse_y - step)
        elif action == 'mouse_down':
            page.bot_mouse_y = min(viewport['height'], page.bot_mouse_y + step)
        elif action == 'mouse_left':
            page.bot_mouse_x = max(0, page.bot_mouse_x - step)
        elif action == 'mouse_right':
            page.bot_mouse_x = min(viewport['width'], page.bot_mouse_x + step)

        page.mouse.move(page.bot_mouse_x, page.bot_mouse_y)

    elif action == 'click':
        # Click at the current stored location if it exists, otherwise center
        if hasattr(page, 'bot_mouse_x'):
            page.mouse.click(page.bot_mouse_x, page.bot_mouse_y)
        else:
            page.mouse.click(400, 300)

class RLBotGUI:
    def __init__(self, root):
        self.root = root

        # RL Setup
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = SimpleDQN(1, len(ACTIONS)).to(self.device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)

        # Reward Model Setup
        self.reward_model = RewardModel(1).to(self.device)
        self.ensure_model_downloaded()

        try:
            # We use weights_only=True to prevent potential security warnings or issues with pickle
            self.reward_model.load_state_dict(torch.load(MODEL_FILE, map_location=self.device, weights_only=True))
            print("Successfully loaded Reward Model weights.")
        except Exception as e:
            print(f"Warning: Could not load reward model weights: {e}. Using uninitialized weights.")

        self.reward_model.eval() # Since it just predicts, we keep it in eval mode

        self.memory = ReplayBuffer(5000)
        self.batch_size = 32
        self.gamma = 0.99
        self.epsilon = 1.0
        self.epsilon_min = 0.1
        self.epsilon_decay = 0.995

        self.bot_thread = None
        self.root.title("RL Game Bot")

        self.target_url = tk.StringVar(value="https://chromedino.com/")
        self.exp_folder = tk.StringVar()
        self.is_running = False

        # URL Selection
        ttk.Label(self.root, text="Game URL:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        ttk.Entry(self.root, textvariable=self.target_url, width=40).grid(row=0, column=1, padx=10, pady=10)

        # Experience Folder Selection
        ttk.Label(self.root, text="Experience Folder:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        ttk.Entry(self.root, textvariable=self.exp_folder, width=40, state="readonly").grid(row=1, column=1, padx=10, pady=10)
        ttk.Button(self.root, text="Browse", command=self.browse_folder).grid(row=1, column=2, padx=10, pady=10)

        # Controls
        self.start_btn = ttk.Button(self.root, text="Start", command=self.toggle_bot)
        self.start_btn.grid(row=2, column=1, pady=20)

    def ensure_model_downloaded(self):
        if not os.path.exists(MODEL_FILE):
            print(f"Reward model not found locally. Downloading from {MODEL_URL}...")
            try:
                # We mock the download if example.com is used, to avoid real network errors in this demo
                if "example.com" in MODEL_URL:
                    print("Using mock download for demo domain...")
                    # Save a dummy state dict using the initialized weights
                    torch.save(self.reward_model.state_dict(), MODEL_FILE)
                else:
                    urllib.request.urlretrieve(MODEL_URL, MODEL_FILE)
                print("Download complete.")
            except Exception as e:
                print(f"Failed to download model: {e}")

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.exp_folder.set(folder)

    def toggle_bot(self):
        if not self.target_url.get():
            messagebox.showerror("Error", "Please enter a target URL.")
            return
        if not self.exp_folder.get():
            messagebox.showerror("Error", "Please select an experience folder.")
            return

        self.is_running = not self.is_running
        if self.is_running:
            self.start_btn.config(text="Stop")
            print(f"Bot started. URL: {self.target_url.get()}, Folder: {self.exp_folder.get()}")
            self.bot_thread = threading.Thread(target=self.run_bot)
            self.bot_thread.start()
        else:
            self.start_btn.config(text="Start")
            print("Bot stopped.")

    def run_bot(self):
        exp_dir = self.exp_folder.get()
        url = self.target_url.get()

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context()
                page = context.new_page()
                page.goto(url)

                self._rl_loop(page, exp_dir)

                browser.close()

        except Exception as e:
            print(f"Playwright error: {e}")
            self.is_running = False
            self.root.after(0, lambda: self.start_btn.config(text="Start"))

    def _rl_loop(self, page, exp_dir):
        state = capture_page(page)
        if state is None:
            print("Failed to capture initial state.")
            self.is_running = False
            self.root.after(0, lambda: self.start_btn.config(text="Start"))
            return

        episode = 0
        step_count = 0

        while self.is_running:
            # Epsilon-greedy action selection
            if random.random() < self.epsilon:
                action = random.randrange(len(ACTIONS))
            else:
                state_tensor = torch.FloatTensor(state).unsqueeze(0).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    q_values = self.model(state_tensor)
                action = q_values.argmax().item()

            # Perform action
            perform_action(page, action)

            # Wait a bit for the game to react
            time.sleep(0.1)

            # Capture next state
            next_state = capture_page(page)
            if next_state is None:
                continue

            # Use the RewardModel to evaluate the frame
            with torch.no_grad():
                ns_tensor = torch.FloatTensor(next_state).unsqueeze(0).unsqueeze(0).to(self.device)
                pred_reward, pred_done = self.reward_model(ns_tensor)

                reward = pred_reward.item()
                # If probability of done is > 0.5, we consider the episode finished
                done = pred_done.item() > 0.5

            # Store experience
            self.memory.push(state, action, reward, next_state, done)

            # Save experience to disk occasionally
            if step_count % 100 == 0:
                exp_path = os.path.join(exp_dir, f"exp_{episode}_{step_count}.npy")
                np.save(exp_path, {'state': state, 'action': action, 'reward': reward, 'next_state': next_state, 'done': done})

            # Train
            if len(self.memory) > self.batch_size:
                states, actions, rewards, next_states, dones = self.memory.sample(self.batch_size)

                states = torch.FloatTensor(states).unsqueeze(1).to(self.device)
                actions = torch.LongTensor(actions).to(self.device)
                rewards = torch.FloatTensor(rewards).to(self.device)
                next_states = torch.FloatTensor(next_states).unsqueeze(1).to(self.device)
                dones = torch.FloatTensor(dones).to(self.device)

                curr_q = self.model(states).gather(1, actions.unsqueeze(1)).squeeze(1)
                with torch.no_grad():
                    next_q = self.model(next_states).max(1)[0]
                target_q = rewards + (1 - dones) * self.gamma * next_q

                loss = nn.MSELoss()(curr_q, target_q)

                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()

            state = next_state
            step_count += 1

            if self.epsilon > self.epsilon_min:
                self.epsilon *= self.epsilon_decay

            if step_count > 1000: # Dummy episode length
                episode += 1
                step_count = 0
                print(f"Episode {episode} completed. Epsilon: {self.epsilon:.3f}")

if __name__ == "__main__":
    root = tk.Tk()
    app = RLBotGUI(root)
    root.mainloop()
