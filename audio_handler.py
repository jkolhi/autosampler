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
        self.stream = None
        self.monitoring = False
        self.current_samplerate = 48000
        self.device_index = None
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
    
    def create_stream(self, device_index, channels, samplerate, channel_map=None):
        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()
            
            self.device_index = device_index
            self.channel_map = channel_map
            self.current_samplerate = samplerate
            
            # Calculate total channels needed
            total_channels = max(channel_map) + 1 if channel_map else channels
            
            # Create duplex stream
            self.stream = sd.Stream(
                device=(device_index, sd.default.device[1]),  # Input, default output
                channels=(total_channels, 2),  # Input channels, stereo output
                callback=self.audio_callback,
                samplerate=samplerate
            )
            self.stream.start()
            return self.stream
            
        except Exception as e:
            debug_print(f"Stream creation error: {e}")
            raise

    def audio_callback(self, indata, outdata, frames, time, status):
        try:
            # Get mapped channels
            data = indata[:, self.channel_map] if self.channel_map else indata
            
            # Update level meter
            level = float(np.max(np.abs(data)))
            self.level_queue.put_nowait(level)
            
            # Store audio for recording
            self.audio_queue.put_nowait(data.copy())
            
            # Route to output if monitoring
            if self.monitoring:
                if data.shape[1] == 1:  # Mono to stereo
                    outdata[:] = np.column_stack((data, data))
                else:  # Stereo as-is or first two channels
                    outdata[:, :2] = data[:, :2]
            else:
                outdata.fill(0)
                
        except Exception as e:
            debug_print(f"Callback error: {e}")

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
            if self.stream:
                self.stream.start()
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

    def stop_stream(self):
        """Stop and cleanup stream"""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None