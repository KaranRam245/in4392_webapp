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

    if len(args) < 2 or args[1] == 'instance_manager':
        print('[INFO] Initiating bootcall Instance Manager..')
        im.start_instance()
    elif len(args) > 3:
        if args[1] == 'node_manager':
            print('[INFO] Initiating bootcall Node Manager..')
            nm.start_instance(host=args[2])
        elif args[1] == 'worker' or args[0] == 'node_worker':
            print('[INFO] Initiating bootcall Worker..')
            nw.start_instance(host=args[2])  # TODO: create start_instance for node workers.
        elif args[1] == 'resource_manager':
            print('[INFO] Initiating bootcall Resource Manager..')
            rm.start_instance(host=args[2])  # TODO: create start_instance for resource managers.
        else:
            print('[ERROR] Unknown argument passed to program {}\n'
                  'Expected "instance_manager", "node_manager", "worker", or '
                  '"resource_manager"'.format(args[1]))
    else:
        print('Not enough arguments provided. Expected "python src/main.py <node> [ip]".\n'
              '[ip] is only optional if <node> is not "instance_manager".')
    print('Program terminated..')


# Main function to start the InstanceManager
if __name__ == '__main__':
    print('Main function called..')
    main()
