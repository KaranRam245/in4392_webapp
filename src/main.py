"""
Main function to be called when starting the AWS main instance.
"""
import sys
sys.path.append('./src')

import aws.instancemanager.instancemanager as im
import aws.nodemanager.nodemanager as nm
import aws.nodeworker.nodeworker as nw


def main():
    args = list(sys.argv)

    if len(args) < 2 or args[1] == 'instance_manager':
        print('[INFO] Initiating bootcall Instance Manager..')
        im.start_instance()
    elif len(args) >= 4:
        if args[1] == 'node_manager':
            print('[INFO] Initiating bootcall Node Manager..')
            nm.start_instance(host=args[2], instance_id=args[3])
        elif args[1] == 'worker' or args[0] == 'node_worker':
            print('[INFO] Initiating bootcall Worker..')
            if len(args) < 5:
                print("[ERROR] workers need an host adddress of the Node Manager.\n"
                      "python src/main.py worker [IM ip] [worker_instance_id] [NM ip]")
                return
            nw.start_instance(host_im=args[2], host_nm=args[4], instance_id=args[3])
        else:
            print('[ERROR] Unknown argument passed to program {}\n'
                  'Expected "instance_manager", "node_manager", or "worker"'.format(args[1]))
    else:
        print(
            'Not enough arguments provided. '
            'Expected "python src/main.py <node> [ip] [instance_id]".\n'
            '[ip] is only optional if <node> is not "instance_manager".')
    print('Program terminated..')


# Main function to start the InstanceManager
if __name__ == '__main__':
    print('Main function called..')
    main()
