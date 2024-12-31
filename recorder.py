"""Recording functionality"""
import threading
import time
import queue
import numpy as np

class AudioRecorder:
    def __init__(self, audio_handler, gui_callback):
        self.audio_handler = audio_handler
        self.gui_callback = gui_callback
        self.recording = False
        self.running = True
        
        # Recording parameters
        self.threshold = 0.01
        self.silence_timeout = 1.0
        self.output_dir = "recordings"
    
    def start_recording(self):
        """Start the recording process"""
        self.recording = True
        threading.Thread(target=self.record_loop, daemon=True).start()
    
    def stop_recording(self):
        """Stop the recording process"""
        self.recording = False
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        self.recording = False
    
    def record_loop(self):
        """Main recording loop"""
        while self.recording and self.running:
            try:
                self.gui_callback("status_update", "Waiting for sound...")
                recorded_chunks = []
                
                # Wait for trigger sound
                while self.recording and self.running:
                    try:
                        data = self.audio_handler.audio_queue.get(timeout=0.1)
                        level = float(np.max(np.abs(data)))
                        print(f"Current level: {level:.3f}")
                        
                        if level > self.threshold:
                            recorded_chunks = [data]
                            print(f"\nStarted recording:")
                            print(f"  Trigger level: {level:.3f}")
                            print(f"  Data shape: {data.shape}")
                            self.gui_callback("status_update", "Recording...")
                            break
                    except queue.Empty:
                        continue
                
                if not (self.recording and self.running):
                    break
                
                # Record until silence timeout
                silence_start = None
                while self.recording and self.running:
                    try:
                        data = self.audio_handler.audio_queue.get(timeout=0.1)
                        level = float(np.max(np.abs(data)))
                        recorded_chunks.append(data)
                        
                        if level < self.threshold:
                            if silence_start is None:
                                silence_start = time.time()
                                print(f"Silence detected: {level:.3f}")
                            else:
                                silence_duration = time.time() - silence_start
                                if silence_duration >= self.silence_timeout:
                                    print(f"\nSaving recording:")
                                    print(f"  Total chunks: {len(recorded_chunks)}")
                                    print(f"  First chunk shape: {recorded_chunks[0].shape}")
                                    filename = self.audio_handler.save_recording(
                                        recorded_chunks,
                                        self.output_dir
                                    )
                                    if filename:
                                        self.gui_callback("recording_saved", filename)
                                    break
                        else:
                            silence_start = None
                            
                    except queue.Empty:
                        continue
                    
            except Exception as e:
                print(f"Error in record_loop: {e}")
                self.gui_callback("error", str(e))
                time.sleep(1)