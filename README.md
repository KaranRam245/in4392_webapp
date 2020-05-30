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
1. Go to `https://console.aws.amazon.com/iam` and create a new user.
2. Assign to the user the permissions you need.
3. Add the user to the group `AmazonEC2ContainerRegistryReadOnly`.
4. Download the access keys or at least remember them.
5. Run in the console `aws configure`.
6. Fill in the data of the access keys from the CSV you downloaded in step 4.

### Setup Streamlit application on AWS
1. First step is to create an AWS EC2 server. We choose a Linux system.
2. Run `sudo yum install python36`. We want need to install Python3.6 (or higher).
3. Run `sudo yum install git`. For the installation of git.
4. Run `git clone https://github.com/KaranRam245/in4392_webapp.git`. Clone the repository.
5. Run `sudo python36 -m pip install streamlit`. Install streamlit.
6. Run `sudo alternatives --set python /usr/bin/python3.6`. We need to set Python3.6 (or higher) to the default version.
7. Run `alias python=python3`. Set the alias of `python` to the newer version so you do not use 2.7 anymore.
8. Run `sudo yum install python36-pip`. Install the pip for python3.6 (or higher).
9. Run `export LC_ALL=en_US.utf-8`. Set the right encoding value. The default does not work with streamlit.
10. Run `export LANG=en_US.utf-8`.
11. Run `sudo python -m pip install --upgrade --force pip`. Upgrade pip.
12. (Optionally) Run `pip install --no-cache-dir tensorflow==2.2.0`. This step is required if your EC2 memory is too small to install TensorFlow with caching.
13. Run `pip install -r requirements.txt`. This installs are additional requirements.
14. And finally `streamlit run app.py`. Have fun :).
15. To enable for connections to the streamlit, create a new inbound rule in your security group for TCP access with the right port. Default is `8502`.
