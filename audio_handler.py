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
        self.device_index = None  # Add device index tracking
        self.monitoring = False
        self.monitor_stream = None
        
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
            # Store device index
            self.device_index = device_index
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

    def start_monitoring(self):
        """Start audio monitoring"""
        try:
            self.monitoring = True
            device = sd.default.device[1]
            
            if self.monitor_stream:
                self.monitor_stream.stop()
                self.monitor_stream.close()
            
            # Calculate max channels needed
            max_channels = max(self.channel_map) + 1 if self.channel_map else self.current_channels
            
            self.monitor_stream = sd.Stream(
                device=(self.device_index, device),
                channels=max_channels,  # Request enough channels for mapping
                callback=self.monitor_callback,
                samplerate=self.current_samplerate
            )
            
            print(f"\nStarting monitoring:")
            print(f"  Input device: {self.device_index}")
            print(f"  Output device: {device}")
            print(f"  Total channels: {max_channels}")
            print(f"  Active channels: {self.channel_map}")
            print(f"  Samplerate: {self.current_samplerate}")
            
            self.monitor_stream.start()
            
        except Exception as e:
            print(f"Error starting monitoring: {e}")

    def stop_monitoring(self):
        """Stop audio monitoring"""
        try:
            self.monitoring = False
            if self.monitor_stream:
                self.monitor_stream.stop()
                self.monitor_stream.close()
                self.monitor_stream = None
            print("Monitoring stopped")
        except Exception as e:
            print(f"Error stopping monitoring: {e}")
    
    def monitor_callback(self, indata, outdata, frames, time, status):
        """Callback for monitoring audio"""
        if status:
            print(f"Status: {status}")
        
        try:
            # Get mapped channels only
            if self.channel_map:
                data = indata[:, self.channel_map]
            else:
                data = indata
                
            # Copy to output (first N channels)
            outdata[:, :data.shape[1]] = data
            
            # Calculate level from active channels
            level = float(np.max(np.abs(data)))
            self.level_queue.put_nowait(level)
            
            # Store audio for recording
            self.audio_queue.put_nowait(data.copy())
            
        except Exception as e:
            print(f"Error in monitor callback: {e}")