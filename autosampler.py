import pyaudio
import wave
import numpy as np
import time
from datetime import datetime
import os

class AudioSampler:
    def __init__(self, 
                 threshold=0.01,           # Audio level threshold to trigger recording
                 silence_timeout=2.0,      # Seconds of silence before stopping
                 format=pyaudio.paFloat32,
                 channels=1,
                 rate=44100,
                 chunk_size=1024,
                 output_dir="recordings"):
        
        self.threshold = threshold
        self.silence_timeout = silence_timeout
        self.format = format
        self.channels = channels
        self.rate = rate
        self.chunk_size = chunk_size
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Initialize PyAudio
        self.p = pyaudio.PyAudio()
        
    def get_input_device(self):
        """Find the index of the default input device"""
        default_input = self.p.get_default_input_device_info()
        return default_input['index']
    
    def start_sampling(self):
        """Main sampling loop"""
        try:
            # Open input stream
            stream = self.p.open(format=self.format,
                               channels=self.channels,
                               rate=self.rate,
                               input=True,
                               input_device_index=self.get_input_device(),
                               frames_per_buffer=self.chunk_size)
            
            print("Listening for audio...")
            
            while True:
                # Check audio level
                data = np.frombuffer(stream.read(self.chunk_size), dtype=np.float32)
                level = np.max(np.abs(data))
                
                if level > self.threshold:
                    self.record_audio(stream)
                    
                time.sleep(0.1)  # Short sleep to prevent CPU overuse
                
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            stream.stop_stream()
            stream.close()
            self.p.terminate()
    
    def record_audio(self, input_stream):
        """Record audio until silence is detected"""
        print("Recording...")
        
        frames = []
        silence_start = None
        
        while True:
            data = input_stream.read(self.chunk_size)
            frames.append(data)
            
            # Check audio level
            audio_data = np.frombuffer(data, dtype=np.float32)
            level = np.max(np.abs(audio_data))
            
            # Handle silence detection
            if level <= self.threshold:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start >= self.silence_timeout:
                    break
            else:
                silence_start = None
        
        # Save the recording
        if frames:
            filename = os.path.join(
                self.output_dir,
                f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            )
            self.save_recording(frames, filename)
            print(f"Saved: {filename}")
            print("Listening for audio...")
    
    def save_recording(self, frames, filename):
        """Save the recorded frames to a WAV file"""
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(frames))
        wf.close()

if __name__ == "__main__":
    # Create and start the sampler
    sampler = AudioSampler(
        threshold=0.01,          # Adjust this value based on your microphone and environment
        silence_timeout=2.0,     # Seconds of silence before stopping recording
        output_dir="recordings"  # Directory where recordings will be saved
    )
    sampler.start_sampling()