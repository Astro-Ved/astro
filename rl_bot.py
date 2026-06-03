import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pygetwindow as gw
import os
import mss
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import random
from collections import deque

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

def capture_window(window_title, resize_dim=(84, 84)):
    """Captures the target window, converts to grayscale and resizes for potato PC."""
    try:
        windows = gw.getWindowsWithTitle(window_title)
        if not windows:
            return None
        win = windows[0]

        # bounding box of the window
        monitor = {
            "top": win.top,
            "left": win.left,
            "width": win.width,
            "height": win.height
        }

        with mss.mss() as sct:
            sct_img = sct.grab(monitor)

            # Convert to numpy array
            img = np.array(sct_img)

            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)

            # Resize to smaller dimensions (e.g. 84x84 is standard for DQN)
            resized = cv2.resize(gray, resize_dim, interpolation=cv2.INTER_AREA)

            return resized
    except Exception as e:
        print(f"Error capturing window: {e}")
        return None

import threading
import time
import pyautogui

# Example action space: Up, Down, Left, Right, None
ACTIONS = ['up', 'down', 'left', 'right', 'space']

def perform_action(action_idx):
    if action_idx < len(ACTIONS):
        pyautogui.press(ACTIONS[action_idx])

class RLBotGUI:
    def __init__(self, root):
        self.root = root

        # RL Setup
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = SimpleDQN(1, len(ACTIONS)).to(self.device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        self.memory = ReplayBuffer(5000)
        self.batch_size = 32
        self.gamma = 0.99
        self.epsilon = 1.0
        self.epsilon_min = 0.1
        self.epsilon_decay = 0.995

        self.bot_thread = None
        self.root.title("RL Game Bot")

        self.target_window = tk.StringVar()
        self.exp_folder = tk.StringVar()
        self.is_running = False

        # Window Selection
        ttk.Label(root, text="Select Target Window:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.window_combobox = ttk.Combobox(root, textvariable=self.target_window, width=40)
        self.window_combobox.grid(row=0, column=1, padx=10, pady=10)
        self.refresh_windows()

        ttk.Button(root, text="Refresh", command=self.refresh_windows).grid(row=0, column=2, padx=10, pady=10)

        # Experience Folder Selection
        ttk.Label(root, text="Experience Folder:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        ttk.Entry(root, textvariable=self.exp_folder, width=40, state="readonly").grid(row=1, column=1, padx=10, pady=10)
        ttk.Button(root, text="Browse", command=self.browse_folder).grid(row=1, column=2, padx=10, pady=10)

        # Controls
        self.start_btn = ttk.Button(root, text="Start", command=self.toggle_bot)
        self.start_btn.grid(row=2, column=1, pady=20)

    def refresh_windows(self):
        windows = [w.title for w in gw.getWindowsWithTitle('') if w.title]
        # Filter for Chrome windows as requested
        chrome_windows = [w for w in windows if 'Google Chrome' in w or 'Chrome' in w]
        self.window_combobox['values'] = chrome_windows if chrome_windows else windows
        if self.window_combobox['values']:
            self.window_combobox.current(0)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.exp_folder.set(folder)

    def toggle_bot(self):
        if not self.target_window.get():
            messagebox.showerror("Error", "Please select a target window.")
            return
        if not self.exp_folder.get():
            messagebox.showerror("Error", "Please select an experience folder.")
            return

        self.is_running = not self.is_running
        if self.is_running:
            self.start_btn.config(text="Stop")
            print(f"Bot started. Window: {self.target_window.get()}, Folder: {self.exp_folder.get()}")
            self.bot_thread = threading.Thread(target=self.run_bot)
            self.bot_thread.start()
        else:
            self.start_btn.config(text="Start")
            print("Bot stopped.")

    def run_bot(self):
        window_title = self.target_window.get()
        exp_dir = self.exp_folder.get()

        state = capture_window(window_title)
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
            perform_action(action)

            # Wait a bit for the game to react
            time.sleep(0.1)

            # Capture next state
            next_state = capture_window(window_title)
            if next_state is None:
                continue

            # Dummy reward (in a real game you'd read the score from the screen or memory)
            reward = 0.1
            done = False # Dummy done flag

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
