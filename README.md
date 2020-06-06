# Toxic_Comments_Model
Sentiment analysis on kaggle toxic comments dataset using 1D convnets &amp; LSTM

## Installation guide for AWS.
Create an AWS account and verify your account. After that we create an instance and connect using SSH. Do not forget to set your permissions to ensure a connection to the server.

### Connect to an AWS instance
1. Create a security group with the following inboud rules

| HTTP       | TCP | 80   | Anywhere         | HTTP anywhere |
|------------|-----|------|------------------|---------------|
| HTTP       | TCP | 80   | Anywhere         | HTTP anywhere |
| Custom TCP | TCP | 8501/8502 | Anywhere/Your IP | Streamlit TCP |
| Custom TCP | TCP | 8501/8502 | Anywhere/Your IP | Streamlit TCP |
| SSH        | TCP | 22   | Your IP          | SSH access    |

2. (Optional) Create an Elastic IP to remove the need for a long DNS name.
3. Create an SSH key pair and save it on a secure location.
4. Run `chmod 400 keypair.pem` on the keypair you created<sup>1</sup>.
5. Connect to your instance using `ssh -i keypair.pem ec-2user@instance-public-dns`

<sup>1</sup> For Ubuntu users you can use a default console. For Windows users, please consider installing the Ubuntu console from the Windows store. This will save you some headaches caused by PuttY ;).

### Setup user permissions
1. Run `sudo apt install awscli`.<sup>*</sup>
2. Go to `https://console.aws.amazon.com/iam` and create a new user.
3. Assign to the user the permissions you need.
4. Add the user to the group `AmazonEC2ContainerRegistryReadOnly`,`AmazonS3ReadOnlyAccess`, and `AmazonS3FullAccess`.
5. Download the access keys or at least remember them.
6. Run in the console `sudo aws configure`.<sup>*</sup>
7. Fill in the data of the access keys from the CSV you downloaded in step 4 with the region name of your AWS instance. My region is, for example, `eu-central-1`. Then set default output format to `json`.<sup>*</sup>

<sup>*</sup> __Any step indicated should be repeated for each new instance installed__

### Instance naming
We name all our instances for the system to know which role each instance might have. In future releases, one could rename instances on the fly. To rename manually, click in the `Name` column on the AWS console and type the right name. The naming conventions are listed below.
- For the instance manager nodes we give the name `Instance Manager`.
- For the node manager we give the name `Node Manager`.
- For worker nodes we give the name `Worker`.
- For the resource managers we give the name `Resource Manager`.

### Install essentials on instance
1. First step is to create an AWS EC2 server. We choose a Linux system.
2. Run `sudo apt-get update -y`.
<<<<<<< HEAD
3. Run `alias python=python3`. Set the alias of `python` to the newer version so you do not use 2.7 anymore.
4. We want to use Python3.6 (or higher). Check this with `python -V`.
=======
3. We want to use Python3.6 (or higher). Check this with `python -V` or `python3 -V`. Otherwise install python 3.6+ with, for example, `sudo yum install -v python3`.
4. Run `alias python=python3`. Set the alias of `python` to the newer version so you do not use 2.7 anymore.
>>>>>>> master
5. Run `sudo apt install python3-pip`. When installed with Yum, you might want to issue `python -m pip install --upgrade pip`.
6. Check with `git --version` if you have git installed. If not, run `sudo yum install git` if you have yum installed or `sudo apt-get install git`.
7. Run `sudo git clone https://github.com/KaranRam245/in4392_webapp.git` to clone the repository.
8. Move into the folder with `cd in4392_webapp/`.
9. (Optionally) Run `pip3 install --no-cache-dir tensorflow==2.2.0`. This step is required if your EC2 memory is too small to install TensorFlow with caching. Alternatively, you could run `pip3 install --no-cache-dir -r requirements.txt` instead of the below step.
10. Run `pip3 install -r requirements.txt`. This installs are additional requirements. In case `psutil` does not install, run `sudo apt-get install -y gcc` (or `sudo yum -y install gcc`) first. If it still does not work, try `yum search python3 | grep devel` followed by `sudo yum install pythonXX-devel` (depending on what is returned with the search) and try install `psutil` again.

#### Side notes
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
To run the application, simply run `python src/main.py instance_manager`. Other instances can be called with `python src/main.py <instance_type> <ip>` where `instance_type` is `resource_manager`, `worker`, or `resource_manager` and `ip` is the public ipv4-address of the instance manager.
