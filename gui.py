"""GUI implementation for the audio auto sampler"""
import tkinter as tk
from tkinter import ttk, filedialog
import queue
import threading
import time
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
import json
import os
from tkinter import messagebox

from audio_handler import AudioHandler
from recorder import AudioRecorder
from config import *

class AudioSamplerGUI:
    def __init__(self, root, settings, settings_file):
        # Core initialization
        self.root = root
        self.settings = settings
        self.settings_file = settings_file
        
        # Initialize settings values
        self.output_dir = settings['output_dir']
        
        # Create queues first
        self.level_queue = queue.Queue()
        
        # Initialize audio components with queue
        self.audio_handler = AudioHandler(self.level_queue)
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="5")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Initialize GUI variables
        self.running = True
        self.recording = False
        self.monitoring = False
        
        # Setup rest of GUI
        self.setup_dark_theme()
        self.setup_gui()
        
        # Initialize recorder
        self.recorder = AudioRecorder(self.audio_handler, self.handle_recorder_callback)
        
        # Start level monitoring
        self.update_level_display()

    def toggle_monitoring(self):
        """Toggle audio monitoring state"""
        if self.monitor_var.get():
            self.audio_handler.start_monitoring()
            self.update_status("Monitoring enabled")
        else:
            self.audio_handler.stop_monitoring()
            self.update_status("Monitoring disabled")    

    def delayed_init(self):
        """Initialize audio devices and apply settings after delay"""
        try:
            # Update interface options first
            self.update_input_options()
            
            # Set saved interface
            if self.settings["interface"]:
                self.interface_var.set(self.settings["interface"])
                # Add small delay before setting input
                self.root.after(500, self.restore_input_settings)
                
        except Exception as e:
            debug_print(f"Error in delayed init: {e}")

    def restore_input_settings(self):
        """Restore input and mode settings"""
        try:
            # Update input options for selected interface
            self.update_input_options()
            
            # Set saved input and mode
            if self.settings["input"]:
                self.input_var.set(self.settings["input"])
            if self.settings["mode"]:
                self.channel_var.set(self.settings["mode"])
                
            # Apply changes
            self.on_selection_change()
            
        except Exception as e:
            debug_print(f"Error restoring input settings: {e}")

    def on_selection_change(self, event=None):
        """Handle changes in interface, input, or mode selection"""
        was_monitoring = False
        
        if hasattr(self, 'monitor_var') and self.monitor_var.get():
            was_monitoring = True
            self.audio_handler.stop_monitoring()
        
        self.restart_monitoring()
        
        if was_monitoring:
            self.audio_handler.start_monitoring()
        
        # Save settings after change
        self.save_settings()
    
    def start_monitoring(self):
        """Start or restart audio input stream"""
        try:
            device = self.get_selected_device()
            if not device:
                return
                
            channels = self.get_input_channels()
            self.audio_handler.create_stream(
                device['index'],
                len(channels),
                device['samplerate'],
                channels
            )
            self.update_status("Audio stream started")
            
        except Exception as e:
            self.update_status(f"Stream error: {e}")

    def stop_monitoring(self):
        """Stop audio monitoring"""
        self.monitoring = False
        self.audio_handler.stop_stream()
        self.update_status("Monitoring stopped")

    def restart_monitoring(self):
        """Restart audio monitoring with new settings"""
        if hasattr(self, 'stream'):
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                print(f"Error stopping stream: {e}")
        
        self.start_monitoring()
    
    def setup_dark_theme(self):
        """Configure dark theme for GUI elements"""
        style = ttk.Style()
        style.configure('TLabel', foreground=TEXT_COLOR, background=DARK_BG)
        style.configure('TFrame', background=DARK_BG)
        style.configure('TButton', foreground='black', background='white')
        style.configure('TCombobox', foreground='black', background='white')
        style.configure('Horizontal.TScale', background=DARK_BG)
        self.root.configure(bg=DARK_BG)
        
    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding="10", style='TFrame')
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Status Text
        self.status_text = tk.Text(main_frame, height=3, width=50, bg=DARKER_BG, fg=TEXT_COLOR)
        self.status_text.grid(row=8, column=0, columnspan=3, sticky='ew', pady=5)
        self.status_text.insert('1.0', "Ready")
        self.status_text.config(state='disabled')
        
        # Audio Interface Selection
        ttk.Label(main_frame, text="Audio Interface:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.interface_var = tk.StringVar()
        self.interface_combo = ttk.Combobox(
            main_frame,
            textvariable=self.interface_var,
            state="readonly"
        )
        
        # Get input devices
        self.input_devices = self.audio_handler.get_input_devices()
        self.interface_combo['values'] = [f"{d['index']}: {d['name']}" for d in self.input_devices]
        
        if self.input_devices:
            self.interface_combo.set(self.interface_combo['values'][0])
        self.interface_combo.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.interface_combo.bind('<<ComboboxSelected>>', self.update_input_options)
        
        # Input Channel Selection
        ttk.Label(main_frame, text="Input:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.input_var = tk.StringVar()
        self.input_combo = ttk.Combobox(
            main_frame,
            textvariable=self.input_var,
            state="readonly"
        )
        self.input_combo.config(width=COMBOBOX_WIDTH)
        self.input_combo.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=5)
        self.input_combo.bind('<<ComboboxSelected>>', self.on_selection_change)
        
        # Channel Mode Selection (Mono/Stereo)
        ttk.Label(main_frame, text="Mode:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.channel_var = tk.StringVar(value="Mono")
        self.channel_combo = ttk.Combobox(
            main_frame,
            textvariable=self.channel_var,
            values=["Mono", "Stereo"],
            state="readonly"
        )
        self.channel_combo.config(width=10)
        self.update_input_options()
        self.channel_combo.grid(row=2, column=1, sticky=tk.W, pady=5)
        self.channel_combo.bind('<<ComboboxSelected>>', self.on_selection_change)
                
        # Output Directory Selection
        ttk.Label(main_frame, text="Output Directory:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.output_dir_var = tk.StringVar(value=self.output_dir)
        ttk.Entry(main_frame, textvariable=self.output_dir_var).grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_output_dir).grid(row=3, column=2, pady=5)
        
        # Threshold Setting
        ttk.Label(main_frame, text="Threshold Level:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.threshold_var = tk.DoubleVar(value=DEFAULT_THRESHOLD)
        threshold_scale = ttk.Scale(
            main_frame,
            from_=THRESHOLD_MIN,
            to=THRESHOLD_MAX,
            variable=self.threshold_var,
            orient=tk.HORIZONTAL,
            command=self.update_threshold
        )
        threshold_scale.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5)
        self.threshold_value_label = ttk.Label(main_frame, text=f"{DEFAULT_THRESHOLD:.3f}")
        self.threshold_value_label.grid(row=4, column=2, sticky=tk.W, pady=5)
        
        # Silence Duration Setting
        ttk.Label(main_frame, text="Silence Duration (sec):").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.silence_timeout_var = tk.DoubleVar(value=DEFAULT_SILENCE_TIMEOUT)
        silence_scale = ttk.Scale(
            main_frame, 
            from_=0.1, 
            to=5.0,
            variable=self.silence_timeout_var, 
            orient=tk.HORIZONTAL
        )
        silence_scale.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=5)
        self.silence_value_label = ttk.Label(main_frame, text=f"{DEFAULT_SILENCE_TIMEOUT:.1f} sec")
        self.silence_value_label.grid(row=5, column=2, sticky=tk.W, pady=5)
        silence_scale.configure(command=self.update_silence_label)
        
        # Controls Frame
        controls_frame = ttk.LabelFrame(main_frame, text="Controls", padding="5")
        controls_frame.grid(row=6, column=0, columnspan=3, sticky='ew', pady=5)
        
        # Monitor Enable Toggle
        self.monitor_var = tk.BooleanVar(value=False)
        self.monitor_toggle = ttk.Checkbutton(
            controls_frame,
            text="Enable Monitoring",
            variable=self.monitor_var,
            command=self.toggle_monitoring
        )
        self.monitor_toggle.grid(row=0, column=0, padx=5)
        
        # Record Button
        self.record_button = ttk.Button(
            controls_frame, 
            text="Start Recording",
            command=self.toggle_recording
        )
        self.record_button.grid(row=0, column=1, padx=5)
        
        # Level Monitor Frame
        monitor_frame = ttk.Frame(main_frame)
        monitor_frame.grid(row=7, column=0, columnspan=3, pady=10, sticky='nsew')
        
        # Setup level monitor
        self.setup_level_monitor(monitor_frame)
        
        # Apply saved settings
        if self.settings["interface"]:
            self.interface_var.set(self.settings["interface"])
            self.update_input_options()
        if self.settings["input"]:
            self.input_var.set(self.settings["input"])
        if self.settings["mode"]:
            self.channel_var.set(self.settings["mode"])
        self.threshold_var.set(self.settings["threshold"])
        self.silence_timeout_var.set(self.settings["silence_timeout"])
        self.output_dir_var.set(self.settings["output_dir"])
        
        return main_frame    
    
    def update_input_options(self, event=None):
        """Update available input options based on selected device"""
        device = self.get_selected_device()
        if device:
            max_channels = device['channels']
            inputs = []
            
            # Add mono input options
            for i in range(max_channels):
                inputs.append(f"Input {i+1} (Mono)")
            
            # Add stereo pair options
            for i in range(0, max_channels-1, 2):
                inputs.append(f"Inputs {i+1}/{i+2} (Stereo)")
            
            self.input_combo['values'] = inputs
            if inputs:
                self.input_combo.set(inputs[0])
            
            # Update channel mode options
            self.channel_combo['values'] = ["Mono", "Stereo"] if max_channels >= 2 else ["Mono"]
            self.channel_combo.set("Mono")
            
            # Trigger monitoring restart
            self.restart_monitoring()
    
    def get_selected_device(self):
        """Get the currently selected audio device info"""
        if not self.interface_var.get():
            return None
        idx = int(self.interface_var.get().split(':')[0])
        return next((d for d in self.input_devices if d['index'] == idx), None)
    
    def get_input_channels(self):
        """Get the input channel(s) based on selection"""
        input_str = self.input_var.get()
        mode = self.channel_var.get()
        
        if not input_str:
            return [0]
            
        try:
            # For stereo pair selections (e.g. "Inputs 1/2 (Stereo)")
            if "Inputs" in input_str and "/" in input_str:
                numbers = input_str.split("(")[0].strip()
                channels = [int(n)-1 for n in numbers.replace("Inputs", "").strip().split("/")]
                return channels if mode == "Stereo" else [channels[0]]
                
            # For single input selections (e.g. "Input 1 (Mono)")
            else:
                channel = int(''.join(filter(str.isdigit, input_str))) - 1
                if mode == "Stereo":
                    return [channel, min(channel + 1, self.get_selected_device()['channels'] - 1)]
                return [channel]
                
        except Exception as e:
            print(f"Error parsing input channels: {e}")
            print(f"Input string: '{input_str}'")
            print(f"Mode: {mode}")
            return [0]
    
    def setup_level_monitor(self, parent_frame):
        """Setup the level monitoring display"""
        try:
            import matplotlib
            print("Matplotlib backend:", matplotlib.get_backend())
            matplotlib.use('TkAgg')
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            print("Successfully imported matplotlib")
            
            # Create figure
            self.fig = Figure(figsize=(8, 2), dpi=100, facecolor=DARK_BG)
            print("Created figure")            
        
            # Initialize data
            self.level_data = np.zeros(LEVEL_HISTORY)
            self.time_data = np.arange(LEVEL_HISTORY)
            
            # Create figure
            self.fig = Figure(figsize=(8, 2), dpi=100, facecolor=DARK_BG)
            self.ax = self.fig.add_subplot(111)
            
            # Configure plot
            self.ax.set_facecolor(DARKER_BG)
            self.ax.set_ylim(0, 1.0)
            self.ax.set_xlim(0, LEVEL_HISTORY)
            self.ax.grid(True, color='#666666', alpha=0.2)
            self.ax.tick_params(colors=TEXT_COLOR)
            
            # Create lines
            self.level_line, = self.ax.plot(self.time_data, self.level_data, color='#00ff00', linewidth=1)
            threshold = self.threshold_var.get()
            self.threshold_line, = self.ax.plot([0, LEVEL_HISTORY], [threshold, threshold], 
                                            color='red', linestyle='--', alpha=0.5)
            
            # Setup canvas in provided frame
            self.canvas = FigureCanvasTkAgg(self.fig, master=parent_frame)
            self.canvas.draw()
            self.canvas_widget = self.canvas.get_tk_widget()
            self.canvas_widget.pack(fill='both', expand=True)
            print("Level monitor setup complete")
        except Exception as e:
            print("Error in setup_level_monitor:", str(e))            

    def update_level_display(self):
        """Update the level monitor display"""
        if not self.running:
            return
            
        try:
            # Process all available levels
            updated = False
            while not self.level_queue.empty():
                self.level_data = np.roll(self.level_data, -1)
                self.level_data[-1] = self.level_queue.get_nowait()
                updated = True
            
            if updated:
                self.level_line.set_ydata(self.level_data)
                self.canvas.draw_idle()
                
        except Exception as e:
            debug_print(f"Level display error: {e}")
        
        # Schedule next update
        if self.running:
            self.root.after(PLOT_UPDATE_INTERVAL, self.update_level_display)
        
    def update_threshold(self, value=None):
        """Update threshold value and display"""
        try:
            threshold = self.threshold_var.get()
            self.threshold_value_label.config(text=f"{threshold:.3f}")
            
            if hasattr(self, 'threshold_line'):
                # Update threshold line position
                self.threshold_line.set_ydata([threshold, threshold])
                
                # Clear old text annotations
                for artist in self.ax.texts:
                    artist.remove()
                
                # Add new threshold label
                self.ax.text(
                    LEVEL_HISTORY - 10,
                    threshold + 0.02,
                    f'Threshold: {threshold:.3f}',
                    color='red',
                    alpha=0.7,
                    horizontalalignment='right'
                )
                
                self.canvas.draw_idle()
                
            if hasattr(self, 'recorder'):
                self.recorder.threshold = threshold
                
            self.save_settings()
            
        except Exception as e:
            debug_print(f"Error updating threshold: {e}")

    def update_status(self, message):
        """Update the status display"""
        self.status_text.config(state='normal')
        self.status_text.delete('1.0', tk.END)
        self.status_text.insert('1.0', message)
        self.status_text.config(state='disabled')
        self.status_text.see(tk.END)
    
    def update_silence_label(self, value=None):
        """Update silence timeout display"""
        timeout = self.silence_timeout_var.get()
        self.silence_value_label.config(text=f"{timeout:.1f} sec")
        if hasattr(self, 'recorder'):
            self.recorder.silence_timeout = timeout
        self.save_settings()
    
    def browse_output_dir(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir = directory
            self.output_dir_var.set(directory)
            if not os.path.exists(directory):
                os.makedirs(directory)
            self.save_settings()
    
    def toggle_recording(self):
        """Toggle recording on/off"""
        if not self.recording:
            self.recording = True
            self.record_button.configure(text="Stop Recording")
            
            # Update recorder parameters
            device = self.get_selected_device()
            self.recorder.threshold = self.threshold_var.get()
            self.recorder.silence_timeout = self.silence_timeout_var.get()
            self.recorder.output_dir = self.output_dir
            self.recorder.samplerate = device['samplerate']
            
            self.recorder.start_recording()
        else:
            self.recording = False
            self.recorder.stop_recording()
            self.record_button.configure(text="Start Recording")
            self.update_status("Recording stopped")
    
    def handle_recorder_callback(self, event_type, data):
        """Handle callbacks from the recorder"""
        if event_type == "status_update":
            self.update_status(data)
        elif event_type == "recording_saved":
            self.update_status(f"Saved: {data}\nWaiting for new sound...")
        elif event_type == "error":
            self.update_status(f"Error: {data}")
    
    def on_closing(self):
        """Cleanup when closing the window"""
        self.save_settings()
        self.running = False
        self.recording = False
        if hasattr(self, 'recorder'):
            self.recorder.cleanup()
        if hasattr(self, 'stream'):
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                print(f"Error closing stream: {e}")
        self.root.destroy()
    
    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    return {**DEFAULT_SETTINGS, **json.load(f)}
        except Exception as e:
            print(f"Error loading settings: {e}")
        return DEFAULT_SETTINGS.copy()

    def save_settings(self):
        """Save current settings to file"""
        try:
            current_settings = {
                "interface": self.interface_var.get(),
                "input": self.input_var.get(),
                "mode": self.channel_var.get(),
                "threshold": self.threshold_var.get(),
                "silence_timeout": self.silence_timeout_var.get(),
                "output_dir": self.output_dir
            }
            with open(self.settings_file, 'w') as f:
                json.dump(current_settings, f, indent=2)
            debug_print("Settings saved")
        except Exception as e:
            debug_print(f"Error saving settings: {e}")

    def prompt_output_directory(self):
        """Prompt user to select output directory"""
        message = "Output directory not found. Please select a directory for recordings."
        messagebox.showinfo("Select Directory", message)
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir = directory
            self.settings["output_dir"] = directory
            if not os.path.exists(directory):
                os.makedirs(directory)
        else:
            # Use default if user cancels
            self.output_dir = DEFAULT_OUTPUT_DIR
            if not os.path.exists(DEFAULT_OUTPUT_DIR):
                os.makedirs(DEFAULT_OUTPUT_DIR)