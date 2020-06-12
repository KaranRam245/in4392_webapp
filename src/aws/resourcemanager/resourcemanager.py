"""
Module for the Resource Manager.
"""
import uuid

import boto3
from botocore.exceptions import ClientError, DataNotFoundError
from aws_logging_handlers.S3 import S3Handler
import logging
from datetime import datetime, timezone

from aws.utils.monitor import Observable
from aws.utils.state import InstanceState
import aws.utils.bucketname as bucketname


class ResourceManagerCore(Observable):

    def __init__(self):
        super().__init__()
        self._instance_state = InstanceState(InstanceState.RUNNING)
        self.s3 = boto3.client('s3')
        self.s3_resource = boto3.resource('s3')
        self.s3_session = boto3.session.Session()
        self.bucket_name = self.initialize_bucket()
        self.logger = Logger()

    def initialize_bucket(self):
        try:
            # Check the bucket list
            bucket_list = self.s3.list_buckets()["Buckets"]
            # If there are no buckets, create a new one
            if not bucket_list:
                self.create_bucket(str(uuid.uuid4()))
                bucket_list = self.s3.list_buckets()["Buckets"]
            # Use the first bucket in the list
            bucket_name = bucket_list[0]["Name"]
            return bucket_name
        except ClientError:
            print("You should add the AmazonS3ReadOnlyAccess and AmazonS3FullAccess "
                  "permission to the user")
            return None

    def create_bucket(self, bucket_name):
        """
        Method called to create a bucket.
        """
        if self.s3_resource.Bucket(bucket_name).creation_date is None:
            current_region = self.s3_session.region_name
            self.logger.log_info("Creating bucket with bucket_name: " + bucket_name + ".")
            self.s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': current_region,
                }
            )
        return bucket_name

    def delete_bucket(self, bucket_name):
        """
        Method called to delete the bucket with the name 'bucket_name'.
        :param bucket_name: Name of the bucket to be deleted.
        """
        if self.s3_resource.Bucket(bucket_name).creation_date is None:
            self.logger.log_error("Bucket " + bucket_name + " does not exist, so it"
                " cannot be deleted.")
            print("Bucket " + bucket_name + " does not exist")
        else:
            self.logger.log_info("Deleting bucket with bucket_name: " + bucket_name)
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
            self.logger.log_error("Bucket " + self.bucket_name + " does not exist, so a"
                " file cannot be uploaded to this bucket.")
            print("Bucket " + self.bucket_name + " does not exist")
        else:
            try:
                self.logger.log_info("Uploading file to bucket " + self.bucket_name + ": " + file_path)
                self.s3.upload_file(file_path, self.bucket_name, key)
            except DataNotFoundError:
                self.logger.log_error("There is no file with file_path " + file_path +
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
            self.logger.log_error("Could not download file with key: {}, as the bucket"
                                    "permissions are wrong!".format(key))
            raise FileNotFoundError("Could not download file with key: {}, as the bucket"
                                    "permissions are wrong!".format(key))
        if self.s3_resource.Bucket(self.bucket_name).creation_date is None:
            self.logger.log_error("Bucket " + self.bucket_name + " does not exist, "
                "so a file cannot be downloaded from it.")
            print("Bucket " + self.bucket_name + " does not exist")
        else:
            try:
                self.s3.download_file(self.bucket_name, key, file_path)
                self.logger.log_info("Downloading file " + file_path + " from the bucket"
                    + self.bucket_name + ".")
            except DataNotFoundError:
                self.logger.log_error("There is no key " + key + " in bucket " + self.bucket_name
                    + "so a file cannot be downloaded from it.")
                print("There is no key " + key + " in bucket " + self.bucket_name)

class Singleton(type):
    """"
    Singleton class to ensure only one logger per instance.
    """
    _instances = {}
    def __call__(cls,*args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Logger(metaclass=Singleton):
    """"
    Class for the logger.
    """

    def __init__(self):
        self.s3 = boto3.client('s3')
        self.s3_resource = boto3.resource('s3')
        self.logger: logging.Logger = logging.getLogger('root')
        self.logger.setLevel(logging.INFO)
        self.s3_session = boto3.session.Session()
        self._log_made = False
        self.create_bucket()


    def log_info(self, message: str):
        self.logger.info(message)
        if not self._log_made:
            self.add_handler()

    def log_error(self, message: str):
        self.logger.error(message)
        if not self._log_made:
            self.add_handler()

    def log_exception(self, message: str):
        self.logger.exception(message)
        if not self._log_made:
            self.add_handler()

    def log_warning(self, message: str):
        self.logger.warning(message)
        if not self._log_made:
            self.add_handler()

    def add_handler(self):
        self._log_made = True
        dt = datetime.now(tz=timezone.utc)
        dt_id = dt.strftime('%Y%m%d%H%M%S')
        s3_handler = S3Handler(dt_id, bucketname.LOGGING_BUCKET_NAME, time_rotation=10)
        self.logger.addHandler(s3_handler)
        print("Using bucket with bucket_name: " + bucketname.LOGGING_BUCKET_NAME + " and key: " + dt_id + ".")

    def create_bucket(self, bucket_name=bucketname.LOGGING_BUCKET_NAME):
        """
        Method called to create a bucket, now in logger to avoid circular dependency.
        """
        if self.s3_resource.Bucket(bucket_name).creation_date is None:
            current_region = self.s3_session.region_name
            self.s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': current_region,
                }
            )

    def close(self):
        self.logger.close()
