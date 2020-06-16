"""
Main function to be called when starting the AWS main instance.
"""
import sys
sys.path.append('./src')

import aws.instancemanager.instancemanager as im
import aws.nodemanager.nodemanager as nm
import aws.nodeworker.nodeworker as nw
from aws.resourcemanager.resourcemanager import log_info, log_error


def main():
    args = list(sys.argv)

    if len(args) < 2 or args[1] == 'instance_manager':
        debug = False
        if 'debug' in args:
            print("Enabling debug mode")
            log_info("Enabling debug mode")
            debug = True
        branch = None
        for arg in args[2:]:
            git_pull_split = str(arg).split('=')
            if git_pull_split[0] == 'git-pull':
                if len(git_pull_split) > 1:
                    branch = git_pull_split[1]
                    print("Enabling git-pull (branch: {}) mode for workers".format(branch))
                    log_info("Enabling git-pull (branch: {}) mode for workers".format(branch))
                else:
                    print("git-pull requires a branch. E.g., git-pull=master")
                    log_info("git-pull requires a branch. E.g., git-pull=master")
        print('[INFO] Initiating bootcall Instance Manager..')
        log_info('Initiating bootcall Instance Manager..')
        im.start_instance(debug=debug, git_pull=branch)
    elif len(args) >= 4:
        if args[1] == 'node_manager':
            # Example: python src/main.py worker [IM ip] [node_manager_id]
            print('[INFO] Initiating bootcall Node Manager..')
            log_info('Initiating bootcall Node Manager..')
            if len(args) < 5:
                print("[ERROR] node managers need the following arguments:\n"
                      "python src/main.py node_manager [IM ip] [NM_instance_id] [account_id]")
                log_error("Node managers need the following arguments:\n"
                      "python src/main.py node_manager [IM ip] [NM_instance_id] [account_id]\nOn:{}".format(args))
                return
            nm.start_instance(im_host=args[2], instance_id=args[3], account_id=args[4])
        elif args[1] == 'worker' or args[0] == 'node_worker':
            print('[INFO] Initiating bootcall Worker..')
            log_info('Initiating bootcall Worker..')
            if len(args) < 6:
                print("[ERROR] workers need an host address of the Node Manager\n"
                      "and an account_id of the user:\n"
                      "python src/main.py worker [IM ip] [worker_instance_id] [account_id] [NM ip]")
                log_error("Workers need an host address of the Node Manager\n"
                      "and an account_id of the user:\n"
                      "python src/main.py worker [IM ip] [worker_instance_id] [account_id] [NM ip]\nOn:{}".format(args))
                return
            nw.start_instance(host_im=args[2], instance_id=args[3], account_id=args[4], host_nm=args[5])
        else:
            print('[ERROR] Unknown argument passed to program {}\n'
                  'Expected "instance_manager", "node_manager", or "worker"'.format(args[1]))
            log_error('Unknown argument passed to program {}\n'
                  'Expected "instance_manager", "node_manager", or "worker"\nOn: {}'.format(args[1], args))
    else:
        print(
            'Not enough arguments provided. '
            'Expected "python src/main.py <node> [ip] [instance_id]".\n'
            '[ip] is only optional if <node> is not "instance_manager".')
        log_error(
            'Not enough arguments provided. '
            'Expected "python src/main.py <node> [ip] [instance_id]".\n'
            '[ip] is only optional if <node> is not "instance_manager".')
    print('Program terminated..')
    log_info('Program terminated..')


# Main function to start the InstanceManager
if __name__ == '__main__':
    print('Main function called..')
    main()
