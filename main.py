"""
Main function to be called when starting the AWS main instance.
"""
import sys
sys.path.append('./src')

import aws


def main():
    args = str(sys.argv)
    print(args)
    if not len(args):
        print('[INFO] Initiating bootcall Instance Manager..')
        aws.instancemanager.instancemanager.start_instance()
    else:
        if args[0] == 'instance_manager':
            print('[INFO] Initiating bootcall Instance Manager..')
            aws.instancemanager.instancemanager.start_instance()
        elif args[0] == 'node_manager':
            print('[INFO] Initiating bootcall Node Manager..')
            aws.nodemanager.nodemanager.start_instance()
        elif args[0] == 'worker' or args[0] == 'node_worker':
            print('[INFO] Initiating bootcall Worker..')
            aws.nodeworker.nodeworker.start_instance()
        elif args[0] == 'resource_manager':
            print('[INFO] Initiating bootcall Resource Manager..')
            aws.resourcemanager.resourcemanager.start_instance()
    print('Program terminated')


# Main function to start the InstanceManager
if __name__ == '__main__':
    print('Main function called..')
    main()
