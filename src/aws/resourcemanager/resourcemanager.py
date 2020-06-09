"""
Module for the Resource Manager.
"""
import uuid

import boto3
from botocore.exceptions import ClientError, DataNotFoundError

import logging
from aws.utils.monitor import Observable
from aws.utils.state import InstanceState


class ResourceManagerCore(Observable):

    def __init__(self):
        super().__init__()
        self._instance_state = InstanceState(InstanceState.RUNNING)
        self.s3 = boto3.client('s3')
        self.s3_resource = boto3.resource('s3')
        self.s3_session = boto3.session.Session()
        self.bucket_name = self.initialize_bucket()

    def initialize_bucket(self):
        try:
            # Check the bucket list
            bucket_list = self.s3.list_buckets()["Buckets"]
            # If there are no buckets, create a new one
            if not bucket_list:
                self.create_bucket()
                bucket_list = self.s3.list_buckets()["Buckets"]
            # Use the first bucket in the list
            bucket_name = bucket_list[0]["Name"]
            return bucket_name
        except ClientError:
            print("You should add the AmazonS3ReadOnlyAccess and AmazonS3FullAccess "
                  "permission to the user")
            return None

    def create_bucket(self):
        """
        Method called to create a bucket.
        """
        bucket_name = str(uuid.uuid4())
        current_region = self.s3_session.region_name
        logging.info("Creating bucket with bucket_name: " + bucket_name + ".")
        self.s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={
                'LocationConstraint': current_region,
            }
        )

    def delete_bucket(self, bucket_name):
        """
        Method called to delete the bucket with the name 'bucket_name'.
        :param bucket_name: Name of the bucket to be deleted.
        """
        if self.s3_resource.Bucket(bucket_name).creation_date is None:
            logging.error("Bucket " + bucket_name + " does not exist, so it"
                " cannot be deleted.")
            print("Bucket " + bucket_name + " does not exist")
        else:
            logging.info("Deleting bucket with bucket_name: " + bucket_name)
            bucket = self.s3_resource.Bucket(bucket_name)
            bucket.object_versions.delete()
            self.s3.delete_bucket(Bucket=bucket_name)

    def upload_file(self, file_path, key):
        """
        Method called to upload a file with path 'file_path' to the bucket with
        name 'bucket_name' and upload it to the storage with name 'key'.
        :param file_path: Path of the file to be uploaded.
        :param bucket_name: Name of the bucket to upload the file to.
        :param key: Name of the key to upload to.
        """
        if self.s3_resource.Bucket(self.bucket_name).creation_date is None:
            logging.error("Bucket " + self.bucket_name + " does not exist, so a"
                " file cannot be uploaded to this bucket.")
            print("Bucket " + self.bucket_name + " does not exist")
        else:
            try:
                logging.info("Uploading file to bucket " + self.bucket_name + ": " + file_path)
                self.s3.upload_file(file_path, self.bucket_name, key)
            except DataNotFoundError:
                logging.error("There is no file with file_path " + file_path +
                    ", so the file cannot be uploaded")
                print("There is no file with file_path " + file_path)

    def download_file(self, key, file_path):
        """
        Method called to download from the bucket with name 'bucket_name' and
        key 'key' and download it to the file with path 'file_path'.
        :param bucket_name: Name of the bucket to download the file from.
        :param key: Name of the key to download from.
        :param file_path: Path of the file to download to.
        """
        if not self.bucket_name:
            logging.error("Could not download file with key: {}, as the bucket"
                                    "permissions are wrong!".format(key))
            raise FileNotFoundError("Could not download file with key: {}, as the bucket"
                                    "permissions are wrong!".format(key))
        if self.s3_resource.Bucket(self.bucket_name).creation_date is None:
            logging.error("Bucket " + self.bucket_name + " does not exist, "
                "so a file cannot be downloaded from it.")
            print("Bucket " + self.bucket_name + " does not exist")
        else:
            try:
                self.s3.download_file(self.bucket_name, key, file_path)
                logging.info("Downloading file " + file_path + " from the bucket"
                    + self.bucket_name + ".")
            except DataNotFoundError:
                logging.error("There is no key " + key + " in bucket " + self.bucket_name
                    + "so a file cannot be downloaded from it.")
                print("There is no key " + key + " in bucket " + self.bucket_name)
