import tkinter as tk
from unittest.mock import patch

# Mock tkinter to bypass display errors
with patch('tkinter.Tk'):
    import rl_bot
    root = tk.Tk()
    app = rl_bot.RLBotGUI(root)
    print("GUI object created successfully")
