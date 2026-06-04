import tkinter as tk
from unittest.mock import patch

with patch('tkinter.Tk'):
    import rl_bot
    print("Successfully imported rl_bot and instantiated variables")
