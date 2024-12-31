#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog
import sounddevice as sd
import soundfile as sf
import numpy as np
import queue
import threading
import time
from datetime import datetime
import os
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation

class AudioSamplerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Sampler")
        self.root.geometry("800x600")
        
        # Audio parameters
        self.samplerate = 44100
        self.channels = 1
        self.threshold = 0.01
        self.silence_timeout = 1.0
        self.output_dir = "recordings"
        
        # Thread-safe queues
        self.audio_queue = queue.Queue()
        self.level_queue = queue.Queue()
        
        # State flags
        self.recording = False
        self.monitoring = False
        self.running = True
        
        # Configure style for dark theme
        self.setup_dark_theme()
        self.setup_gui()
        self.setup_level_monitor()
        
        # Bind cleanup to window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_dark_theme(self):
        style = ttk.Style()
        style.configure('TLabel', foreground='white', background='#2E2E2E')
        style.configure('TFrame', background='#2E2E2E')
        style.configure('TButton', foreground='black', background='white')
        style.configure('TCombobox', foreground='black', background='white')
        style.configure('Horizontal.TScale', background='#2E2E2E')
        self.root.configure(bg='#2E2E2E')
        
    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding="10", style='TFrame')
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Audio Interface Selection
        ttk.Label(main_frame, text="Audio Interface:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.interface_var = tk.StringVar()
        self.interface_combo = ttk.Combobox(main_frame, textvariable=self.interface_var, width=50)
        
        # Get input devices
        devices = sd.query_devices()
        self.input_devices = []
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                self.input_devices.append({
                    'index': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'samplerate': device['default_samplerate']
                })
                self.interface_combo['values'] = [
                    f"{d['index']}: {d['name']}" 
                    for d in self.input_devices
                ]
        
        if self.input_devices:
            self.interface_combo.set(self.interface_combo['values'][0])
        self.interface_combo.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.interface_combo.bind('<<ComboboxSelected>>', self.update_channel_options)
        
        # Channel Selection
        ttk.Label(main_frame, text="Channels:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.channel_var = tk.StringVar(value="Mono")
        self.channel_combo = ttk.Combobox(main_frame, textvariable=self.channel_var, width=10)
        self.update_channel_options()  # Initialize channel options
        self.channel_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Output Directory Selection
        ttk.Label(main_frame, text="Output Directory:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.output_dir_var = tk.StringVar(value=self.output_dir)
        ttk.Entry(main_frame, textvariable=self.output_dir_var).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_output_dir).grid(row=2, column=2, pady=5)
        
        # Threshold Setting
        ttk.Label(main_frame, text="Threshold:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.threshold_var = tk.DoubleVar(value=self.threshold)
        threshold_scale = ttk.Scale(main_frame, from_=0.001, to=0.1, 
                                  variable=self.threshold_var, orient=tk.HORIZONTAL)
        threshold_scale.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Silence Duration Setting
        ttk.Label(main_frame, text="Silence Duration (sec):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.silence_timeout_var = tk.DoubleVar(value=self.silence_timeout)
        silence_scale = ttk.Scale(main_frame, from_=0.1, to=5.0,
                                variable=self.silence_timeout_var, orient=tk.HORIZONTAL)
        silence_scale.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5)
        self.silence_value_label = ttk.Label(main_frame, text=f"{self.silence_timeout:.1f} sec", style='TLabel')
        self.silence_value_label.grid(row=4, column=2, sticky=tk.W, pady=5)
        silence_scale.configure(command=self.update_silence_label)
        
        # Level Monitor
        self.fig = Figure(figsize=(8, 2), dpi=100, facecolor='#2E2E2E')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#1E1E1E')
        self.ax.tick_params(colors='white')
        for spine in self.ax.spines.values():
            spine.set_edgecolor('white')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=main_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=5, column=0, columnspan=3, pady=10)
        
        # Control Buttons
        button_frame = ttk.Frame(main_frame, style='TFrame')
        button_frame.grid(row=6, column=0, columnspan=3, pady=10)
        
        self.monitor_button = ttk.Button(button_frame, text="Start Monitoring", 
                                       command=self.toggle_monitoring)
        self.monitor_button.grid(row=0, column=0, padx=5)
        
        self.record_button = ttk.Button(button_frame, text="Start Recording", 
                                      command=self.toggle_recording)
        self.record_button.grid(row=0, column=1, padx=5)
        
        # Status bar - Using Text widget for better message display
        self.status_text = tk.Text(main_frame, height=3, width=50, bg='#1E1E1E', fg='white')
        self.status_text.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.status_text.insert('1.0', "Ready")
        self.status_text.config(state='disabled')

    def update_silence_label(self, value):
        """Update the silence duration label when the slider moves"""
        self.silence_value_label.configure(text=f"{float(value):.1f} sec")
    
    def update_channel_options(self, event=None):
        """Update available channel options based on selected device"""
        device = self.get_selected_device()
        if device:
            max_channels = device['channels']
            if max_channels >= 2:
                self.channel_combo['values'] = ["Mono", "Stereo"]
            else:
                self.channel_combo['values'] = ["Mono"]
            self.channel_combo.set("Mono")  # Default to Mono
    
    def setup_level_monitor(self):
        """Setup the level monitoring display"""
        self.level_data = np.zeros(100)
        self.threshold_line = self.ax.axhline(y=self.threshold, color='r', linestyle='--')
        self.level_line, = self.ax.plot(range(len(self.level_data)), self.level_data, 'g-')
        self.ax.set_ylim(0, 0.2)
        self.ax.set_title('Audio Level Monitor', color='white')
        
        # Use explicit save_count to avoid warning
        self.anim = animation.FuncAnimation(
            self.fig, self.update_plot, 
            interval=50, blit=True, save_count=100
        )
    
    def update_status(self, message):
        """Update the status text widget with a new message"""
        self.status_text.config(state='normal')
        self.status_text.delete('1.0', tk.END)
        self.status_text.insert('1.0', message)
        self.status_text.config(state='disabled')
        self.status_text.see(tk.END)
    
    def update_plot(self, frame):
        """Update the level monitor plot"""
        try:
            # Update level data from queue
            while not self.level_queue.empty():
                self.level_data = np.roll(self.level_data, -1)
                self.level_data[-1] = self.level_queue.get_nowait()
            
            self.level_line.set_ydata(self.level_data)
            self.threshold_line.set_ydata([self.threshold_var.get(), self.threshold_var.get()])
            
            return self.level_line, self.threshold_line
        except Exception as e:
            print(f"Error updating plot: {e}")
            return self.level_line, self.threshold_line
    
    def browse_output_dir(self):
        """Open directory browser dialog"""
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir_var.set(directory)
            self.output_dir = directory
    
    def get_selected_device(self):
        """Get the currently selected audio device info"""
        if not self.interface_var.get():
            return None
        idx = int(self.interface_var.get().split(':')[0])
        return next((d for d in self.input_devices if d['index'] == idx), None)
    
    def get_channel_count(self):
        """Get the number of channels based on mono/stereo selection"""
        return 2 if self.channel_var.get() == "Stereo" else 1
    
    def audio_callback(self, indata, frames, time, status):
        """Callback function for audio stream"""
        if status:
            print(f"Status: {status}")
            return
        
        try:
            level = float(np.max(np.abs(indata)))
            self.level_queue.put_nowait(level)
            
            if self.recording:
                self.audio_queue.put_nowait(indata.copy())
        except queue.Full:
            pass
        except Exception as e:
            print(f"Error in audio callback: {e}")
    
    def toggle_monitoring(self):
        """Toggle audio monitoring on/off"""
        if not self.monitoring:
            try:
                device = self.get_selected_device()
                if not device:
                    self.update_status("Error: No audio device selected")
                    return
                
                self.stream = sd.InputStream(
                    device=device['index'],
                    channels=self.get_channel_count(),
                    samplerate=int(device['samplerate']),
                    callback=self.audio_callback
                )
                self.stream.start()
                self.monitoring = True
                self.monitor_button.configure(text="Stop Monitoring")
                self.update_status("Monitoring audio levels...")
            except Exception as e:
                self.update_status(f"Error: {str(e)}")
        else:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                print(f"Error stopping stream: {e}")
            self.monitoring = False
            self.monitor_button.configure(text="Start Monitoring")
            self.update_status("Monitoring stopped")
    
    def toggle_recording(self):
        """Toggle recording on/off"""
        if not self.recording:
            if not self.monitoring:
                self.toggle_monitoring()
            if self.monitoring:
                self.recording = True
                self.record_button.configure(text="Stop Recording")
                self.update_status("Waiting for sound...")
                threading.Thread(target=self.record_audio, daemon=True).start()
        else:
            self.recording = False
            self.record_button.configure(text="Start Recording")
            self.update_status("Recording stopped")
    
    def record_audio(self):
        """Main recording loop that continuously monitors for audio and creates new recordings"""
        while self.recording and self.running:
            try:
                # Wait for sound above threshold to start a new recording
                self.update_status("Waiting for sound...")
                recorded_chunks = []
                
                # Wait for trigger sound
                while self.recording and self.running:
                    try:
                        data = self.audio_queue.get(timeout=0.1)
                        level = float(np.max(np.abs(data)))
                        if level > self.threshold_var.get():  # Start recording when ABOVE threshold
                            # Start new recording
                            recorded_chunks = [data]
                            print(f"New recording started - level: {level:.4f}")
                            self.update_status("Recording...")
                            break
                    except queue.Empty:
                        continue
                
                if not (self.recording and self.running):
                    break
                
                # Active recording phase
                silence_start = None
                
                # Record until silence timeout
                while self.recording and self.running:
                    try:
                        data = self.audio_queue.get(timeout=0.1)
                        level = float(np.max(np.abs(data)))
                        recorded_chunks.append(data)
                        
                        # Check for silence (level BELOW threshold)
                        if level < self.threshold_var.get():
                            if silence_start is None:
                                silence_start = time.time()
                                print(f"Silence detected - level: {level:.4f}")
                            else:
                                silence_duration = time.time() - silence_start
                                if silence_duration >= self.silence_timeout_var.get():
                                    print(f"Silence timeout reached - saving recording")
                                    self.save_recording(recorded_chunks)
                                    break  # Break to start waiting for new sound
                        else:
                            silence_start = None  # Reset silence timer if sound goes above threshold
                            
                    except queue.Empty:
                        continue
                    
            except Exception as e:
                print(f"Error in record_audio: {e}")
                self.update_status(f"Error: {str(e)}")
                time.sleep(1)  # Brief pause before retrying

    def save_recording(self, chunks):
        """Save the recorded chunks to a new WAV file"""
        if not chunks:
            return
            
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
            
            # Create unique filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(
                self.output_dir,
                f"recording_{timestamp}.wav"
            )
            
            data = np.vstack(chunks)
            sf.write(filename, data, int(self.get_selected_device()['samplerate']))
            
            # Update status with save confirmation and next action
            status_message = f"Saved: recording_{timestamp}.wav\nWaiting for new sound..."
            print(f"Saved recording to: {filename}")
            self.root.after(0, lambda: self.update_status(status_message))
            
        except Exception as e:
            print(f"Error saving recording: {e}")
            self.update_status(f"Error saving recording: {str(e)}")

    def on_closing(self):
        """Cleanup when closing the window"""
        self.running = False
        self.recording = False
        if hasattr(self, 'stream'):
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                print(f"Error closing stream: {e}")
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AudioSamplerGUI(root)
    root.mainloop()
