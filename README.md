# SentiCloud - a Cloud-based Toxic Comments Model
Sentiment analysis on kaggle toxic comments dataset using 1D convnets &amp; LSTM

## Installation guide for AWS.
Create an AWS account and verify your account. After that we create an instance and connect using SSH. Do not forget to set your permissions to ensure a connection to the server.

### Connect to an AWS instance
1. Create a security group with the following inboud rules. The distinction `Anywhere/Your IP` should in this development phase be `Your IP`.

| HTTP       | TCP | 80        | Source                       | HTTP anywhere    |
|:-----------|:----|:----------|:-----------------------------|:-----------------|
| HTTP       | TCP | 80        | Anywhere/Your IP             | HTTP anywhere    |
| Custom TCP | TCP | 8501/8502 | Anywhere/Your IP             | Streamlit TCP    |
| Custom TCP | TCP | 8501/8502 | Anywhere/Your IP             | Streamlit TCP    |
| Custom TCP | TCP | 8080      | Public IPv4 of each instance | Connection to IM |
| Custom TCP | TCP | 8081      | Public IPv4 of each instance | Connection to NM |
| SSH        | TCP | 22        | Your IP                      | SSH access       |

2. (Optional) Create an Elastic IP to remove the need for a long DNS name.
3. Create an SSH key pair and save it on a secure location.
4. Run `chmod 400 keypair.pem` on the keypair you created<sup>1</sup>.
5. Connect to your instance using `ssh -i keypair.pem ec-2user@instance-public-dns`

<sup>1</sup> For Ubuntu users you can use a default console. For Windows users, please consider installing the Ubuntu console from the Windows store. This will save you some headaches caused by PuttY ;).

### Setup user permissions
1. Run `sudo apt install awscli`.<sup>*</sup>
2. Go to `https://console.aws.amazon.com/iam` and create a new user. Add the checkmarks at the bottom to give the permissions to the user.
3. Assign to the user the permissions you need.
    - E.g: `AmazonEC2ContainerRegistryReadOnly`,`AmazonEc2FullAccess`, `AmazonSSMFullAccess`, and `AmazonS3FullAccess`.
5. Download the access keys or at least remember them.
6. Run in the console `sudo aws configure`.<sup>*</sup>
7. Fill in the data of the access keys from the CSV you downloaded in step 4 with the region name of your AWS instance. My region is, for example, `eu-central-1`. Then set default output format to `json`.<sup>*</sup>

<sup>*</sup> __Any step indicated should be repeated for each new instance installed__

### Instance naming
We name all our instances for the system to know which role each instance might have. In future releases, one could rename instances on the fly. To rename manually, click in the `Name` column on the AWS console and type the right name. The naming conventions are listed below.
- For the instance manager nodes we give the name `Instance Manager`.
- For the node manager we give the name `Node Manager`.
- For worker nodes we give the name `Worker`.

### Install essentials on the Instance Manager
Before continuing this read, be aware that for any problems you may find, there might be a solution available in the _Trouble shooting_ section below.
1. First step is to create an AWS EC2 server. We choose a Linux system. We strongly recommend to create an Elastic IP for each instance.
2. Before starting the instance, go to `Actions > Instance Settings > Attach/Replace IAM Role`.
3. Attach the `EC2-SSM` access role (if this role does not exist yet, do substeps below. Otherwise skip to next main step).
    - Click `Create new IAM role` and then `Create Role`.
    - Click `EC2` and `Next: Permissions`.
    - Attach `AmazonEC2RoleforSSM`, click next, and give the name `EC2-SSM`.
    - Go back to instance to attach the newly created role to the instance (i.e., go back to step 3). If the instance was running, restart.
4. Start the instance and SSH connect with the instance.
5. Install the SSM agent:
    - Run `cd /tmp`
    - Run `sudo yum install -y https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_amd64/amazon-ssm-agent.rpm`
    - Run `sudo start amazon-ssm-agent`. It will probably tell you it was already running.
    - Verify the agent is running with `aws ssm describe-instance-information` and check if the instanceid is in the list.
6. Run `sudo apt-get update -y`.
7. We want to use Python3.6 (or higher). Check this with `python -V` or `python3 -V`. Otherwise install python 3.6+ with, for example, `sudo yum install python3`.
8. Run `alias python=python3`. Set the alias of `python` to the newer version so you do not use 2.7 anymore.
9. Run `sudo apt install python3-pip`. When installed with Yum, you might want to issue `python -m pip install --upgrade pip`.
10. Check with `git --version` if you have git installed. If not, run `sudo yum install git` if you have yum installed or `sudo apt-get install git`.
11. Run `sudo git clone https://github.com/KaranRam245/in4392_webapp.git` to clone the repository.
12. Move into the folder with `cd in4392_webapp/`.
13. (Optionally) Run `pip3 install --no-cache-dir tensorflow==2.2.0`. This step is required if your EC2 memory is too small to install TensorFlow with caching. Alternatively, you could run `pip3 install --no-cache-dir -r requirements.txt` instead of the below step.
14. Run `pip3 install -r requirements.txt`. This installs are additional requirements. In case `psutil` does not install, run `sudo apt-get install -y gcc` (or `sudo yum -y install gcc`) first. If it still does not work, try `yum search python3 | grep devel` followed by `sudo yum install pythonXX-devel` (depending on what is returned with the search) and try install `psutil` again.

#### Installing a new Worker/Node manager
1. Create a new Instance on the AWS console with `Launch Instance`.
2. We choose `Amazon Linux 2 AMI (HVM) SSD Volume Type 64-bit (x86)`.
3. Choose some Instance type. For the example we choose `t2.micro`.
4. `Next Configure Instance Details`.
5. Assign the IAM role `EC2-SSM`.
6. Click a few times on Next until you can choose the security group and assign the earlier created security group.
    - Please do not forget you should add this new instance to the security group for TCP 8080 and 8081!
7. `Review and Launch` and `Launch` and set your KeyPair you should have created earlier.
8. While the instance is starting, we could assign an Elastic IP-address which prevents our progress from being lost.
    - Allocate an Elastic IP Address and Associate with the new instance. Do not forget to release Elastic IP-addresses if you delete your instance!
9. Rename your new instance to `Node Manager` or `Worker`. You can do this in the `Name` column and by clicking the pencil icon.
10. Connect to the instance through SSH.
11. Go to the root user role, as the SSM connections go to `root` users. You can do this with `sudo su` and `yum update`.
12. Run `aws configure` and fill in the keys you obtained earlier (see _Setup user permissions_).
13. Install the SSM agent:
    - Run `cd /tmp`
    - Run `yum install -y https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_amd64/amazon-ssm-agent.rpm`
    - Verify the agent is running with `aws ssm describe-instance-information` and check if the instanceid is in the list.
14. Run `yum install -y python3`.
15. Run `python3 -m pip install --upgrade pip`.
16. Run `yum install -y git`.
17. Clone this git with `git clone https://github.com/KaranRam245/in4392_webapp.git`.
18. Run `cd in4392_webapp/`.
19. Run `python3 -m pip install --no-cache-dir tensorflow==2.2.0`.
20. Run `yum install -y gcc`.
21. Run `yum search python3 | grep devel`, followed by `yum install -y pythonXX-devel` (probably just `yum install python3-devel`).
22. Run `python3 -m pip install -r requirements.txt`.
23. You're done! In case you're in a development, do not forget to `git pull` or `git checkout` the branch you're developing on.

#### Trouble shooting
- `pip` still missing? You may try `sudo easy_install pip`.
- Sometimes there may be some problems with the new instance. One of the problems we found was with the version of python being 2.7.
The below command shows how to change the alternative version to `Python 3.6` if the alias did not do the trick earlier.
  - `sudo alternatives --set python /usr/bin/python3.6`.
- Other problems are with `apt-get` not being available. In these cases try replacing it with `yum` first. Amazon Linux AMI instances use Yum instead of Apt-get.
- If you encounter a `Permissions denied: (...)` error. You may try to add `sudo` in front instead or set the right permissions with, for example, `sudo chmod -R 707` or any other permissions level you need.
- On some systems `pip3` is named `pip` instead.
- If not the right version is installed on you system and you have Yum. Run `sudo yum install python36` and `sudo alternatives --set python /usr/bin/python3.6`. Followed by `sudo yum install python36-pip` and `alias python=python3`.
- In case you receive an `OSError: [Errno 98] Address already in use` error when starting an application you terminated with <kbd>CTRL</kbd> + <kbd>Z</kbd>, you might want to kill the old process. You may do this with `lsof -i:8080` followed by `kill -9 PID`. Please prevent this problem in the future by using <kbd>CTRL</kbd> + <kbd>C</kbd> to safely terminate the program.

### Setup Streamlit application on AWS
For this step, we assume you have done the previous steps successfully.
1. Run `sudo python -m pip3 install streamlit`. Install streamlit.
2. Run `export LC_ALL=en_US.utf-8`. Set the right encoding value. The default does not work with streamlit.
3. Run `export LANG=en_US.utf-8`.
4. And finally `streamlit run app.py`. Have fun :).
5. To enable for connections to the streamlit, create a new inbound rule in your security group for TCP access with the right port. Default is `8502`.

### Run the applications
To run the application, simply run `python src/main.py instance_manager`. Other instances can be called with `python src/main.py <instance_type> <ip> <Account id>` where `instance_type` is `resource_manager`, `worker`, or `resource_manager`, `ip` is the public ipv4-address of the instance manager, and `Account id` is the id of your AWS account found at https://console.aws.amazon.com/billing/home?#/account.

### Sync logs to own filesystem.
1. Connect with AWS (do not forget the `aws configure`).
2. If AWS is not yet installed, do `aws apt-get install awscli`.
3. Then do `aws s3 sync s3://bucketname /logs`.
4. Finally do `tar -zcvf logs.tgz /logs/*`

For all you Windows users, these files can be found in `\\wsl$\Ubuntu\home`.
