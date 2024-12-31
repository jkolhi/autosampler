# Audio Auto Sampler

A Python-based audio sampling application with GUI for recording and monitoring audio inputs. Automatically captures audio when sound exceeds a threshold and stops when silence is detected.

## Features

- Real-time audio level monitoring
- Multiple audio interface support
- Mono/Stereo channel selection
- Automatic recording with configurable triggers
- Audio level visualization
- Dark-themed GUI interface

## Requirements

- Python 3.x
- tkinter
- numpy
- sounddevice
- soundfile
- matplotlib

## Installation

1. Clone the repository
2. Install dependencies:

```bash
pip install numpy sounddevice soundfile matplotlib
```

## Usage

Run the program:

```bash
python main.py
```

### Interface Controls

1. **Audio Interface**: Select your audio input device
2. **Input**: Choose input channel(s)
3. **Mode**: Toggle between Mono/Stereo
4. **Threshold Level**: Set trigger level for recording (0.001 - 0.5)
5. **Silence Duration**: Set silence duration before stopping (0.1 - 5.0 seconds)
6. **Monitor**: Toggle audio monitoring
7. **Record**: Start/Stop automatic recording

### Recording Process

1. Select audio interface and channel(s)
2. Set threshold level and silence duration
3. Click "Start Recording"
4. Program will:
   - Wait for audio above threshold
   - Record until silence is detected
   - Save WAV file to output directory
   - Resume waiting for next sound

### Configuration

Edit `config.py` to customize:

- Default sample rate (44.1kHz/48kHz)
- Default threshold and silence timeout
- Level meter ranges
- GUI appearance
- Debug output

Recordings are saved to the `recordings/` directory by default.
