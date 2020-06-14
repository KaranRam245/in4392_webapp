"""
Module for the Resource Manager.
"""
import asyncio
import logging
import shutil
import os
from datetime import datetime
from pytz import timezone

import boto3
from botocore.exceptions import ClientError, DataNotFoundError

import aws.utils.config as config
from aws.utils.monitor import Observable
from aws.utils.state import InstanceState


# Boolean indicating if the logging is initialized.
INITIALIZED = False


def initialize_logging():
    global INITIALIZED
    logging.basicConfig(filename=config.DEFAULT_LOG_FILE + '.log', level=logging.INFO)
    INITIALIZED = True


class ResourceManagerCore(Observable):

    def __init__(self, instance_id, account_id):
        global INITIALIZED
        super().__init__()
        if not INITIALIZED:
            initialize_logging()
        self._instance_state = InstanceState(InstanceState.RUNNING)
        self.s3 = boto3.client('s3')
        self.s3_resource = boto3.resource('s3')
        self.s3_session = boto3.session.Session()
        self.account_id = account_id
        self.files_bucket = None
        self.logging_bucket = None
        self.initialize_bucket()
        self._instance_id = instance_id

    def initialize_bucket(self):
        try:
            # Create both buckets (one for files and one for logging).
            self.files_bucket = self.create_bucket(self.account_id + "-files")
            self.logging_bucket = self.create_bucket(self.account_id + "-logging")
            bucket_list = self.s3.list_buckets()["Buckets"]
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
            logging.info("Creating bucket with bucket_name: " + bucket_name + ".")
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
            logging.error("Bucket " + bucket_name + " does not exist, so it"
                                                    " cannot be deleted.")
            print("Bucket " + bucket_name + " does not exist")
        else:
            logging.info("Deleting bucket with bucket_name: " + bucket_name)
            bucket = self.s3_resource.Bucket(bucket_name)
            bucket.object_versions.delete()
            self.s3.delete_bucket(Bucket=bucket_name)

    def upload_file(self, file_path, key, bucket_name):
        """
        Method called to upload a file with path 'file_path' to the bucket with
        name 'bucket_name' and upload it to the storage with name 'key'.
        :param file_path: Path of the file to be uploaded.
        :param key: Name of the key to upload to.
        :param bucket_name: The name of the bucket to upload to.
        """
        if self.s3_resource.Bucket(bucket_name).creation_date is None:
            logging.error("Bucket " + bucket_name + " does not exist, so a"
                                                    " file cannot be uploaded to this bucket.")
            print("Bucket " + bucket_name + " does not exist")
        else:
            try:
                logging.info("Uploading file to bucket " + bucket_name + ": " + file_path)
                self.s3.upload_file(file_path, bucket_name, key)
            except DataNotFoundError:
                logging.error("There is no file with file_path " + file_path +
                              ", so the file cannot be uploaded")
                print("There is no file with file_path " + file_path)

    def download_file(self, bucket_name, key, file_path):
        """
        Method called to download from the bucket with name 'bucket_name' and
        key 'key' and download it to the file with path 'file_path'.
        :param bucket_name: Name of the bucket to download the file from.
        :param key: Name of the key to download from.
        :param file_path: Path of the file to download to.
        """
        if not bucket_name:
            logging.error("Could not download file with key: {}, as the bucket"
                          "permissions are wrong!".format(key))
            raise FileNotFoundError("Could not download file with key: {}, as the bucket"
                                    "permissions are wrong!".format(key))
        if self.s3_resource.Bucket(bucket_name).creation_date is None:
            logging.error("Bucket " + bucket_name + " does not exist, "
                                                    "so a file cannot be downloaded from it.")
            print("Bucket " + bucket_name + " does not exist")
        else:
            try:
                self.s3.download_file(bucket_name, key, file_path)
                logging.info("Downloading file " + file_path + " from the bucket"
                             + bucket_name + ".")
            except DataNotFoundError:
                logging.error("There is no key " + key + " in bucket " + bucket_name
                              + "so a file cannot be downloaded from it.")
                print("There is no key " + key + " in bucket " + bucket_name)

    def upload_log(self, clean):
        temporary_copy = config.DEFAULT_LOG_FILE + '_copy.log'
        shutil.copy(config.DEFAULT_LOG_FILE + '.log', temporary_copy)
        if clean:  # If clean, do not keep the log.
            os.remove(config.DEFAULT_LOG_FILE + '.log')
        else:  # If not clean, clear the original.
            with open(config.DEFAULT_LOG_FILE + '.log') as f:
                f.close()
        key = '{}_{}.log'.format(self._instance_id,
                                 datetime.now(timezone('Europe/Amsterdam')).strftime('%Y%m%d%H%M%S'))
        self.upload_file(file_path=temporary_copy, key=key,
                         bucket_name=(self.account_id + '-logging'))
        os.remove(temporary_copy)

    async def period_upload_log(self):
        while True:
            self.upload_log(clean=False)
            await asyncio.sleep(config.LOGGING_INTERVAL)