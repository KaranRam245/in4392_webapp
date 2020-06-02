"""
Main function to be called when starting the AWS main instance.
"""
import sys
sys.path.append('./src')

import aws.instancemanager.instancemanager as im
import aws.nodemanager.nodemanager as nm
import aws.nodeworker.nodeworker as nw
import aws.resourcemanager.resourcemanager as rm


def main():
    args = list(sys.argv)

    if len(args) < 2:
        print('[INFO] Initiating bootcall Instance Manager..')
        im.start_instance()
    else:
        if args[1] == 'instance_manager':
            print('[INFO] Initiating bootcall Instance Manager..')
            im.start_instance()
        elif args[1] == 'node_manager':
            print('[INFO] Initiating bootcall Node Manager..')
            nm.start_instance()
        elif args[1] == 'worker' or args[0] == 'node_worker':
            print('[INFO] Initiating bootcall Worker..')
            nw.start_instance()
        elif args[1] == 'resource_manager':
            print('[INFO] Initiating bootcall Resource Manager..')
            rm.start_instance()
        else:
            print('[ERROR] Unknown argument passed to program {}\n'
                  'Expected "instance_manager", "node_manager", "worker", or '
                  '"resource_manager"'.format(args[1]))
    print('Program terminated')


# Main function to start the InstanceManager
if __name__ == '__main__':
    print('Main function called..')
    main()
