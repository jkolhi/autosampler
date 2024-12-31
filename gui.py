"""GUI implementation for the audio sampler"""
import tkinter as tk
from tkinter import ttk, filedialog
import numpy as np
import queue
import threading
import time
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation

from audio_handler import AudioHandler
from recorder import AudioRecorder
from config import *

class AudioSamplerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Sampler")
        self.root.geometry("800x600")
        
        # Initialize queues
        self.level_queue = queue.Queue()
        
        # Initialize audio handler
        self.audio_handler = AudioHandler(self.level_queue)
        
        # Initialize recorder
        self.recorder = AudioRecorder(self.audio_handler, self.handle_recorder_callback)
        
        # State flags
        self.recording = False
        self.running = True
        
        # Audio parameters
        self.output_dir = DEFAULT_OUTPUT_DIR
        
        # Setup GUI
        self.setup_dark_theme()
        self.setup_gui()  # This will now create status_text first
        self.setup_level_monitor()
        
        # Wait a bit before starting monitoring to ensure GUI is ready
        self.root.after(500, self.update_input_options)  # This will trigger initial monitoring
        
        # Bind cleanup to window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def on_selection_change(self, event=None):
        """Handle changes in interface, input, or mode selection"""
        self.restart_monitoring()
    
    def start_monitoring(self):
        """Start audio monitoring"""
        try:
            device = self.get_selected_device()
            if not device:
                self.update_status("Error: No audio device selected")
                return
            
            channels = self.get_input_channels()
            print(f"Starting monitoring with device {device['index']} and channels {channels}")
            
            self.stream = self.audio_handler.create_input_stream(
                device['index'],
                len(channels),
                device['samplerate'],
                channels
            )
            self.stream.start()
            self.update_status(f"Monitoring audio levels (channels: {channels})")
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            print(f"Error in start_monitoring: {e}")
    
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
        """Setup the main GUI elements"""
        main_frame = ttk.Frame(self.root, padding="10", style='TFrame')
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Status bar (create this first so it's available for status updates)
        self.status_text = tk.Text(main_frame, height=3, width=50, bg=DARKER_BG, fg=TEXT_COLOR)
        self.status_text.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.status_text.insert('1.0', "Ready")
        self.status_text.config(state='disabled')
        
        # Audio Interface Selection
        ttk.Label(main_frame, text="Audio Interface:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.interface_var = tk.StringVar()
        self.interface_combo = ttk.Combobox(main_frame, textvariable=self.interface_var, width=50)
        
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
        self.input_combo = ttk.Combobox(main_frame, textvariable=self.input_var, width=50)
        self.input_combo.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=5)
        self.input_combo.bind('<<ComboboxSelected>>', self.on_selection_change)
        
        # Channel Mode Selection (Mono/Stereo)
        ttk.Label(main_frame, text="Mode:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.channel_var = tk.StringVar(value="Mono")
        self.channel_combo = ttk.Combobox(main_frame, textvariable=self.channel_var, width=10)
        self.update_input_options()  # Initialize input options
        self.channel_combo.grid(row=2, column=1, sticky=tk.W, pady=5)
        self.channel_combo.bind('<<ComboboxSelected>>', self.on_selection_change)
        
        # Output Directory Selection
        ttk.Label(main_frame, text="Output Directory:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.output_dir_var = tk.StringVar(value=self.output_dir)
        ttk.Entry(main_frame, textvariable=self.output_dir_var).grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_output_dir).grid(row=3, column=2, pady=5)
        
        # Threshold Setting
        ttk.Label(main_frame, text="Threshold:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.threshold_var = tk.DoubleVar(value=DEFAULT_THRESHOLD)
        threshold_scale = ttk.Scale(main_frame, from_=0.001, to=0.1, 
                                  variable=self.threshold_var, orient=tk.HORIZONTAL)
        threshold_scale.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Silence Duration Setting
        ttk.Label(main_frame, text="Silence Duration (sec):").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.silence_timeout_var = tk.DoubleVar(value=DEFAULT_SILENCE_TIMEOUT)
        silence_scale = ttk.Scale(main_frame, from_=0.1, to=5.0,
                                variable=self.silence_timeout_var, orient=tk.HORIZONTAL)
        silence_scale.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=5)
        self.silence_value_label = ttk.Label(main_frame, text=f"{DEFAULT_SILENCE_TIMEOUT:.1f} sec", style='TLabel')
        self.silence_value_label.grid(row=5, column=2, sticky=tk.W, pady=5)
        silence_scale.configure(command=self.update_silence_label)
        
        # Setup Level Monitor Figure
        self.fig = Figure(figsize=PLOT_SIZE, dpi=PLOT_DPI, facecolor=DARK_BG)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(DARKER_BG)
        self.ax.tick_params(colors=TEXT_COLOR)
        for spine in self.ax.spines.values():
            spine.set_edgecolor(TEXT_COLOR)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=main_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=6, column=0, columnspan=3, pady=10)
        
        # Control Buttons - Only recording button now
        button_frame = ttk.Frame(main_frame, style='TFrame')
        button_frame.grid(row=7, column=0, columnspan=3, pady=10)
        
        self.record_button = ttk.Button(button_frame, text="Start Recording", 
                                      command=self.toggle_recording)
        self.record_button.grid(row=0, column=0, padx=5)
        
        # Status bar
        self.status_text = tk.Text(main_frame, height=3, width=50, bg=DARKER_BG, fg=TEXT_COLOR)
        self.status_text.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.status_text.insert('1.0', "Ready")
        self.status_text.config(state='disabled')
    
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
    
    def setup_level_monitor(self):
        """Setup the audio level monitoring display"""
        self.level_data = np.zeros(LEVEL_HISTORY)
        self.threshold_line = self.ax.axhline(y=DEFAULT_THRESHOLD, color='r', linestyle='--')
        self.level_line, = self.ax.plot(range(len(self.level_data)), self.level_data, 'g-')
        self.ax.set_ylim(0, 0.2)
        self.ax.set_title('Audio Level Monitor', color=TEXT_COLOR)
        
        self.anim = animation.FuncAnimation(
            self.fig, self.update_plot, 
            interval=PLOT_UPDATE_INTERVAL, blit=True, save_count=LEVEL_HISTORY
        )
    
    def update_plot(self, frame):
        """Update the level monitor plot"""
        try:
            while not self.level_queue.empty():
                self.level_data = np.roll(self.level_data, -1)
                self.level_data[-1] = self.level_queue.get_nowait()
            
            self.level_line.set_ydata(self.level_data)
            self.threshold_line.set_ydata([self.threshold_var.get(), self.threshold_var.get()])
            
            return self.level_line, self.threshold_line
        except Exception as e:
            print(f"Error updating plot: {e}")
            return self.level_line, self.threshold_line
    
    def update_status(self, message):
        """Update the status display"""
        self.status_text.config(state='normal')
        self.status_text.delete('1.0', tk.END)
        self.status_text.insert('1.0', message)
        self.status_text.config(state='disabled')
        self.status_text.see(tk.END)
    
    def update_silence_label(self, value):
        """Update the silence duration label when the slider moves"""
        self.silence_value_label.configure(text=f"{float(value):.1f} sec")
        if hasattr(self, 'recorder'):
            self.recorder.silence_timeout = float(value)
    
    def browse_output_dir(self):
        """Open directory browser dialog"""
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir_var.set(directory)
            self.output_dir = directory
            if hasattr(self, 'recorder'):
                self.recorder.output_dir = directory
    
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