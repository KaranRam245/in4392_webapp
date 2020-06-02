"""
Main function to be called when starting the AWS main instance.
"""
import sys
sys.path.append('./src')

import aws


def main():
    args = str(sys.argv)
    if not len(args):
        aws.instancemanager.instancemanager.start_instance()
    else:
        if args[0] == 'instance_manager':
            aws.instancemanager.instancemanager.start_instance()
        elif args[0] == 'node_manager':
            aws.nodemanager.nodemanager.start_instance()
        elif args[0] == 'worker' or args[0] == 'node_worker':
            aws.nodeworker.nodeworker.start_instance()
        elif args[0] == 'resource_manager':
            aws.resourcemanager.resourcemanager.start_instance()
    print('Program terminated')


# Main function to start the InstanceManager
if __name__ == '__main__':
    print('Main function called..')
    main()
