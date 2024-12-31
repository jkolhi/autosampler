"""Audio handling functionality"""
import sounddevice as sd
import soundfile as sf
import numpy as np
from datetime import datetime
import os
import queue
from config import debug_print

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
            # Get number of channels from first chunk
            num_channels = chunks[0].shape[1]
            
            # Ensure all chunks have same channel count
            fixed_chunks = []
            for chunk in chunks:
                if chunk.shape[1] != num_channels:
                    # Reshape mono to match stereo if needed
                    if num_channels == 2 and chunk.shape[1] == 1:
                        chunk = np.column_stack((chunk, chunk))
                    # Take first channel if going from stereo to mono
                    elif num_channels == 1 and chunk.shape[1] == 2:
                        chunk = chunk[:, 0:1]
                fixed_chunks.append(chunk)
            
            # Concatenate fixed chunks
            data = np.concatenate(fixed_chunks, axis=0)
            
            # Save with proper format
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(output_dir, f"recording_{timestamp}.wav")
            sf.write(filename, data, int(self.current_samplerate))
            
            debug_print(f"\nSaved recording:")
            debug_print(f"  Shape: {data.shape}")
            debug_print(f"  Channels: {num_channels}")
            debug_print(f"  Filename: {filename}")
            
            return filename
            
        except Exception as e:
            debug_print(f"Error saving recording: {e}")
            return None

    def start_monitoring(self):
        """Start audio monitoring"""
        try:
            self.monitoring = True
            if self.monitor_stream:
                self.monitor_stream.stop()
                self.monitor_stream.close()
            
            # Calculate max channels needed
            max_channels = max(self.channel_map) + 1 if self.channel_map else self.current_channels
            
            # Create duplex stream for monitoring
            self.monitor_stream = sd.Stream(
                device=(self.device_index, sd.default.device[1]),  # Input device, default output
                channels=(max_channels, 2),  # Input channels, stereo output
                callback=self.monitor_callback,
                samplerate=self.current_samplerate
            )
            
            debug_print(f"\nStarting monitoring:")
            debug_print(f"  Input device: {self.device_index}")
            debug_print(f"  Output device: {sd.default.device[1]}")
            debug_print(f"  Channels: {max_channels}")
            debug_print(f"  Active channels: {self.channel_map}")
            
            self.monitor_stream.start()
            
        except Exception as e:
            debug_print(f"Error starting monitoring: {e}")
            raise

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
        """Handle audio monitoring callback"""
        if status:
            debug_print(f"Status: {status}")
        
        try:
            # Get mapped channels
            if self.channel_map:
                data = indata[:, self.channel_map]
            else:
                data = indata
                
            # Copy to both output channels (stereo)
            outdata[:, 0] = data[:, 0]  # Left
            if data.shape[1] > 1:
                outdata[:, 1] = data[:, 1]  # Right if stereo
            else:
                outdata[:, 1] = data[:, 0]  # Mono to both channels
            
            # Update level meter
            level = float(np.max(np.abs(data)))
            level = min(level, LEVEL_MAX)  # Clip to max level
            self.level_queue.put_nowait(level)
            
            # Store audio for recording
            self.audio_queue.put_nowait(data.copy())
            
        except Exception as e:
            debug_print(f"Error in monitor callback: {e}")
            debug_print(f"Input shape: {indata.shape}")
            debug_print(f"Output shape: {outdata.shape}")
            debug_print(f"Channel map: {self.channel_map}")