#!/usr/bin/env python3
import tkinter as tk
from gui import AudioSamplerGUI

def main():
    root = tk.Tk()
    app = AudioSamplerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()