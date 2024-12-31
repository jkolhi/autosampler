"""Audio handling functionality"""
import sounddevice as sd
import soundfile as sf
import numpy as np
from datetime import datetime
import os
import queue

class AudioHandler:
    def __init__(self, level_queue):
        self.level_queue = level_queue
        self.audio_queue = queue.Queue()
        self.current_samplerate = 48000  # Default, will be updated when stream is created
        self.current_channels = None
        self.channel_map = None
        
    def get_input_devices(self):
        """Get list of available input devices"""
        devices = sd.query_devices()
        input_devices = []
        
        print("\nAvailable Audio Input Devices:")
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                print(f"\nDevice {i}: {device['name']}")
                print(f"  Max input channels: {device['max_input_channels']}")
                print(f"  Default samplerate: {device['default_samplerate']}")
                
                input_devices.append({
                    'index': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'samplerate': device['default_samplerate']
                })
        
        return input_devices
    
    def create_input_stream(self, device_index, channels, samplerate, channel_map=None):
        """Create and return a new input stream"""
        try:
            print(f"\nCreating input stream:")
            print(f"  Device index: {device_index}")
            print(f"  Channel map: {channel_map}")
            
            self.current_samplerate = int(samplerate)
            self.current_channels = len(channel_map) if channel_map else channels
            self.channel_map = channel_map

            # Request all channels up to highest needed
            max_channel = max(channel_map) + 1 if channel_map else channels
            
            stream = sd.InputStream(
                device=device_index,
                channels=max_channel,
                samplerate=self.current_samplerate,
                callback=self.audio_callback
            )
            
            print(f"  Stream created:")
            print(f"    Samplerate: {self.current_samplerate}")
            print(f"    Total channels: {max_channel}")
            print(f"    Active channels: {channel_map}")
            return stream
            
        except Exception as e:
            print(f"Error creating stream: {e}")
            raise
    
    def audio_callback(self, indata, frames, time, status):
        """Callback function for audio stream"""
        if status:
            print(f"Status: {status}")
            return
        
        try:
            # Extract only the mapped channels
            if self.channel_map:
                data = indata[:, self.channel_map]
            else:
                data = indata
            
            # Store audio data first
            self.audio_queue.put_nowait(data.copy())
            
            # Calculate level from mapped channels
            level = float(np.max(np.abs(data)))
            self.level_queue.put_nowait(level)
            
        except queue.Full:
            print("Queue full")
        except Exception as e:
            print(f"Error in callback: {e}")
            print(f"Input shape: {indata.shape}")
    
    def save_recording(self, chunks, output_dir):
        """Save recorded audio chunks to a WAV file"""
        if not chunks:
            return None
            
        try:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(output_dir, f"recording_{timestamp}.wav")
            
            # Stack chunks and ensure float32 format
            data = np.vstack(chunks)
            data = data.astype(np.float32)
            
            print(f"\nSaving recording:")
            print(f"  Shape: {data.shape}")
            print(f"  Channels: {self.current_channels}")
            print(f"  Samplerate: {self.current_samplerate}")
            print(f"  Max value: {np.max(np.abs(data))}")
            
            sf.write(filename, data, self.current_samplerate)
            return filename
            
        except Exception as e:
            print(f"Error saving: {e}")
            return None