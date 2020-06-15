"""
Module containing default values for the general program.
"""
# How many seconds should the program wait with syncing instance states with boto?
BOTO_UPDATE_SEC = 60

# How many seconds should the program wait until a script should give life?
START_SIGNAL_TIMEOUT = 10

# The amount of seconds a server is allowed to sleep until the same client sends again.
SERVER_SLEEP_TIME = 1

# Time to sleep for the send protocol of a client.
CLIENT_SEND_SLEEP = 0.1

# How many seconds should be between heartbeats for NM? Must be greater than SERVER_SLEEP_TIME.
HEART_BEAT_INTERVAL_NODE_MANAGER = 2

# How many seconds should be between heartbeats for workers? Must be greater than SERVER_SLEEP_TIME.
HEART_BEAT_INTERVAL_WORKER = 3

# How many seconds until a program is deemed dead? Max wait time until heartbeats?
HEART_BEAT_TIMEOUT = 10

# Seconds until a retry is made for initialize when in debugging mode.
DEBUG_INIT_RETRY = 5

# Default parts of the commands.
DEFAULT_DIRECTORY = 'cd /tmp/in4392_webapp/'
# Example: python3 src/main.py node_manager/worker im_ip instance_id account_id (workers add nm_ip).
DEFAULT_MAIN_CALL = 'python3 src/main.py {} {} {} {}'

# Time in seconds to wait for the logger to upload to S3.
LOGGING_INTERVAL = 60

# Default name for the log file.
DEFAULT_LOG_FILE = '/tmp/temporary'

"""
Parameters for Load balancing.
"""
# Size of a time window to check overload metrics on.
# The time span checked is WINDOW_SIZE*HEART_BEAT_INTERVAL seconds.
WINDOW_SIZE = 2

# Percentage 0-100 for which a CPU is deemed to overload.
CPU_OVERLOAD_PERCENTAGE = 99

# Product of WINDOW_SIZE and CPU_OVERLOAD_PERCENTAGE. A value greater or equal to this value
# indicates the CPU has been overloaded during the full window size.
CPU_OVERLOAD_PRODUCT = WINDOW_SIZE * CPU_OVERLOAD_PERCENTAGE

# Percentage 0-100 for which memory is deemed to overload.
MEM_OVERLOAD_PERCENTAGE = 100

# Product of WINDOW_SIZE and MEM_OVERLOAD_PERCENTAGE. A value greater or equal to this value
# indicates the memory has been overloaded during the full window size.
MEM_OVERLOAD_PRODUCT = WINDOW_SIZE * MEM_OVERLOAD_PERCENTAGE

# Maximum allowed jobs per worker. A value above this means there should be a new worker.
MAX_JOBS_PER_WORKER = 5
