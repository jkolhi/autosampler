"""Configuration settings for the audio auto sampler"""

# Default audio settings
DEFAULT_SAMPLERATE = 44100
#DEFAULT_SAMPLERATE = 48000
DEFAULT_CHANNELS = 1
DEFAULT_THRESHOLD = 0.01
DEFAULT_SILENCE_TIMEOUT = 1.0
DEFAULT_OUTPUT_DIR = "recordings"

# Level meter settings
LEVEL_MIN = 0.0          # Minimum level for meter display
LEVEL_MAX = 1.0          # Maximum level for meter display
THRESHOLD_MIN = 0.001    # Minimum threshold value
THRESHOLD_MAX = 0.5      # Maximum threshold value

# GUI theme colors
DARK_BG = '#2E2E2E'
DARKER_BG = '#1E1E1E'
TEXT_COLOR = 'white'

# GUI element sizes
COMBOBOX_WIDTH = 35  # Width for dropdown menus

# Plot settings
PLOT_SIZE = (8, 2)
PLOT_DPI = 100
LEVEL_HISTORY = 100  # Number of points in level history
PLOT_UPDATE_INTERVAL = 50  # milliseconds

# Debug settings
DEBUG_MODE = False  # Set to False to disable debug output

def debug_print(*args, **kwargs):
    """Print debug messages if DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(*args, **kwargs)

# Settings file path
#SETTINGS_FILE = "settings.json"

# Default settings
# DEFAULT_SETTINGS = {
#     "interface": "",
#     "input": "",
#     "mode": "Mono",
#     "threshold": DEFAULT_THRESHOLD,
#     "silence_timeout": DEFAULT_SILENCE_TIMEOUT,
#     "output_dir": DEFAULT_OUTPUT_DIR
# }