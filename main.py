"""
Main function to be called when starting the AWS main instance.
"""
import sys
sys.path.append('./src')
from aws.instancemanager.instancemanager import start_node_scheduler


# Main function to start the InstanceManager
if __name__ == '__main__':
    start_node_scheduler()