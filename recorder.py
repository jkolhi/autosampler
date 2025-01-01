"""Recording functionality"""
import os
import threading
import time
import queue
import numpy as np
from config import debug_print, DEFAULT_OUTPUT_DIR

class AudioRecorder:
    def __init__(self, audio_handler, gui_callback):
        self.audio_handler = audio_handler
        self.gui_callback = gui_callback
        self.recording = False
        self.running = True
        self.threshold = 0.01
        self.silence_timeout = 1.0
        self.output_dir = DEFAULT_OUTPUT_DIR
        self.current_chunks = []
        
        # Create output directory
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def toggle_recording(self):
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        """Start the recording process"""
        self.recording = True
        self.current_chunks = []
        
        # Start recording thread
        threading.Thread(target=self.record_loop, daemon=True).start()
        self.gui_callback("status_update", "Recording started")

    def stop_recording(self):
        """Stop recording and save current file"""
        self.recording = False
        
        # Save any pending recording
        if self.current_chunks:
            filename = self.audio_handler.save_recording(
                self.current_chunks,
                self.output_dir
            )
            if filename:
                self.gui_callback("recording_saved", filename)

    def cleanup(self):
        """Clean up resources"""
        self.running = False
        self.recording = False
    
    def record_loop(self):
        """Main recording loop"""
        while self.recording and self.running:
            try:
                # Get initial audio data
                data = self.audio_handler.audio_queue.get(timeout=0.1)
                level = float(np.max(np.abs(data)))

                # Start recording if above threshold
                if level > self.threshold:
                    debug_print(f"Recording triggered at level: {level:.3f}")
                    self.current_chunks = [data]
                    
                    # Continue recording until silence or manual stop
                    silence_start = None
                    while self.recording and self.running:
                        try:
                            data = self.audio_handler.audio_queue.get(timeout=0.1)
                            level = float(np.max(np.abs(data)))
                            self.current_chunks.append(data)

                            if level < self.threshold:
                                if silence_start is None:
                                    silence_start = time.time()
                                elif time.time() - silence_start >= self.silence_timeout:
                                    self.save_current_recording()
                                    break
                            else:
                                silence_start = None
                                
                        except queue.Empty:
                            continue
                            
            except queue.Empty:
                continue
            except Exception as e:
                debug_print(f"Error in record loop: {e}")
                self.gui_callback("error", str(e))

    def save_current_recording(self):
        if self.current_chunks:
            filename = self.audio_handler.save_recording(
                self.current_chunks,
                self.output_dir
            )
            if filename:
                self.gui_callback("recording_saved", filename)
            self.current_chunks = []