import sounddevice as sd
import soundfile as sf
import numpy as np
import time
from datetime import datetime
import os
import queue

class AudioSampler:
    def __init__(self, 
                 threshold=0.05,          # Audio level threshold to trigger recording
                 silence_timeout=2.0,     # Seconds of silence before stopping
                 samplerate=44100,
                 channels=1,
                 output_dir="recordings"):
        
        self.threshold = threshold
        self.silence_timeout = silence_timeout
        self.samplerate = samplerate
        self.channels = channels
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Queue for audio data
        self.q = queue.Queue()
        
    def audio_callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        self.q.put(indata.copy())
    
    def start_sampling(self):
        """Main sampling loop"""
        try:
            with sd.InputStream(samplerate=self.samplerate,
                              channels=self.channels,
                              callback=self.audio_callback):
                print("Listening for audio...")
                
                while True:
                    # Get audio data from queue
                    try:
                        data = self.q.get(timeout=0.1)
                        level = np.max(np.abs(data))
                        
                        if level > self.threshold:
                            self.record_audio()
                            
                    except queue.Empty:
                        continue
                        
        except KeyboardInterrupt:
            print("\nStopping...")
    
    def record_audio(self):
        """Record audio until silence is detected"""
        print("Recording...")
        
        recorded_data = []
        silence_start = None
        
        while True:
            try:
                data = self.q.get(timeout=0.1)
                recorded_data.append(data)
                
                level = np.max(np.abs(data))
                
                # Handle silence detection
                if level <= self.threshold:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start >= self.silence_timeout:
                        break
                else:
                    silence_start = None
                    
            except queue.Empty:
                continue
        
        # Save the recording
        if recorded_data:
            filename = os.path.join(
                self.output_dir,
                f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            )
            self.save_recording(np.vstack(recorded_data), filename)
            print(f"Saved: {filename}")
            print("Listening for audio...")
    
    def save_recording(self, data, filename):
        """Save the recorded data to a WAV file"""
        sf.write(filename, data, self.samplerate)

if __name__ == "__main__":
    # Create and start the sampler
    sampler = AudioSampler(
        threshold=0.01,          # Adjust this value based on your microphone and environment
        silence_timeout=2.0,     # Seconds of silence before stopping recording
        output_dir="recordings"  # Directory where recordings will be saved
    )
    sampler.start_sampling()