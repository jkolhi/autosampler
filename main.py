#!/usr/bin/env python3
import tkinter as tk
from gui import AudioSamplerGUI
import os
import json
from pathlib import Path

# Settings paths
SETTINGS_DIR = Path.home() / '.autosampler'
SETTINGS_FILE = SETTINGS_DIR / 'settings.json'

def init_settings():
    """Initialize settings directory and file"""
    SETTINGS_DIR.mkdir(exist_ok=True)
    
    # Default settings
    default_settings = {
        'threshold': 0.1,
        'sample_rate': 48000,
        'buffer_size': 1024,
        'level_history': 100,
        'output_dir': str(Path.home() / 'Music' / 'Samples'),
        'interface': '',
        'input': '',
        'mode': 'Mono',
        'silence_timeout': 1.0
    }
    
    # Create or load settings
    if not SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(default_settings, f, indent=2)
        return default_settings, SETTINGS_FILE
    
    # Load existing settings
    try:
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            # Update with any missing defaults
            for key, value in default_settings.items():
                if key not in settings:
                    settings[key] = value
            return settings, SETTINGS_FILE
    except Exception as e:
        print(f"Error loading settings: {e}")
        return default_settings, SETTINGS_FILE

def main():
    settings, settings_file = init_settings()
    root = tk.Tk()
    app = AudioSamplerGUI(root, settings, settings_file)
    root.mainloop()

if __name__ == "__main__":
    main()