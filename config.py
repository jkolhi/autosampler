"""Configuration settings for the audio sampler"""

# Default audio settings
DEFAULT_SAMPLERATE = 44100
DEFAULT_CHANNELS = 1
DEFAULT_THRESHOLD = 0.01
DEFAULT_SILENCE_TIMEOUT = 1.0
DEFAULT_OUTPUT_DIR = "recordings"

# GUI theme colors
DARK_BG = '#2E2E2E'
DARKER_BG = '#1E1E1E'
TEXT_COLOR = 'white'

# Plot settings
PLOT_SIZE = (8, 2)
PLOT_DPI = 100
LEVEL_HISTORY = 100  # Number of points in level history
PLOT_UPDATE_INTERVAL = 50  # milliseconds