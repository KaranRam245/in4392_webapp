"""
Module containing default values for the general program.
"""
# How many seconds should the program wait with syncing instance states with boto?
BOTO_UPDATE_SEC = 60

# Instance configuring retry timeout
INSTANCE_START_CONFIGURE_TIMEOUT = 5

# How many seconds should the program wait until a script should give life?
START_SIGNAL_TIMEOUT = 30

# How many seconds should be between heartbeats?
HEART_BEAT_INTERVAL = 3

# How many seconds until a program is deemed dead? Max wait time until heartbeats?
HEART_BEAT_TIMEOUT = 30

# Seconds until a retry is made for initialize when in debugging mode.
DEBUG_INIT_RETRY = 5

# The name of the bucket in which the logging will be saved.
LOGGING_BUCKET_NAME = "in4392-webapp-group3-logging-bucket"

# Default parts of the commands.
DEFAULT_DIRECTORY = 'cd /tmp/in4392_webapp/'
DEFAULT_MAIN_CALL = 'python3 src/main.py {} {} {}'
