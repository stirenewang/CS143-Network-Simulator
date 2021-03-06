# constants.py
# Contains the constants that other classes and files will use

# Unit Conversions
MB_TO_BYTES = 1000000.0     # Multiplier to convert MB to bytes
KB_TO_BYTES = 1000.0        # Multiplier to convert KB to bytes 
BYTES_TO_MBITS = 0.000008   # Multiplier to convert bytes to megabits
SEC_TO_MS = 1000.0          # Multiplier to convert seconds to milliseconds
MS_TO_SEC = 0.001           # Multiplier to convert milliseconds to seconds

# Packet Sizes
DATA_PKT_SIZE = 1024.0      # Bytes per data packet
ACK_PKT_SIZE = 64.0         # Bytes per acknowledgement packet
RTABLE_PKT_SIZE = 64.0      # Bytes per routing table packet

# Time Delays
CONSECUTIVE_PKT_DELAY = 0.5 # Send new consecutive packets every 0.5 ms 
TIMEOUT_TIME = 500          # Default packet timeout time, otherwise use avg RTT 
FAST_PERIOD = 100           # Time to update window size for Fast TCP
BELLMAN_PERIOD = 5000       # Time between each bellman ford event enqueued (ms)

# Other
DEFAULT_NUM_WINDOWS = 500   # Default window size for windowed averages
DEC_PLACES = 2				# Round the decimal places for analytic's times

# Global Variables
global system_EQ            # the global event queue struct
global system_analytics     # the global analytics class

global debug                # When debugging
global all_flows_done       # Indicates if all flows are completed
global bellman_ford         # If we are running bellman ford

debug = False
bellman_ford = True
