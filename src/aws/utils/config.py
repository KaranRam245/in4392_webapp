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
CLIENT_SEND_SLEEP = 1

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

# Time in seconds to wait for the first log.
LOGGING_START_INTERVAL = LOGGING_INTERVAL

# Default name for the log file.
DEFAULT_LOG_FILE = '/tmp/temporary'

DEFAULT_JOB_LOCAL_DIRECTORY = '/tmp/jobs/'

"""
Parameters for Load balancing.
"""
# Size of a time window to check overload metrics on.
# The time span checked is WINDOW_SIZE*HEART_BEAT_INTERVAL seconds.
WINDOW_SIZE = 2

# Maximum allowed jobs per worker. A value above this means there is a worker overloaded.
MAX_JOBS_PER_WORKER = 5

# Minimum needed jobs per worker. A value equal or below means there is a worker underloaded.
MIN_JOBS_PER_WORKER = 1
