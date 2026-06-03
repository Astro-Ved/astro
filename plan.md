1. *Create `requirements.txt`*
   - Define necessary dependencies for the bot, such as `torch`, `opencv-python`, `mss`, `pygetwindow`, `pyautogui`, and `numpy`.
2. *Create `rl_bot.py`*
   - Implement a generic RL game bot using a lightweight DQN architecture suitable for a "potato PC" (small CNN, low resolution grayscale input).
   - Add a Tkinter GUI to select the target Chrome window, specify the folder for storing experiences, and start/stop the bot.
   - Implement screen capture of the specific window using `mss` and `pygetwindow`.
   - Implement the RL loop (action selection, sending keystrokes via `pyautogui`, capturing the next frame, storing experiences to disk, and training the model).
3. *Complete pre-commit steps*
   - Ensure proper testing, verifications, reviews, and reflections are done.
4. *Submit the change*
   - Submit the new files to the repository.
