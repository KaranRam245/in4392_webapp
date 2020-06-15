"""
Module for the Resource Manager.
"""
import asyncio
import json
import logging
import shutil
import os
import traceback
from datetime import datetime
from pytz import timezone
from time import time

import boto3
from botocore.exceptions import ClientError, DataNotFoundError

import aws.utils.config as config
from aws.utils.monitor import Observable
from aws.utils.state import InstanceState


def log_metric(metric: dict):
    metric['time'] = time()
    logging.info("METRIC{}".format(json.dumps(metric)))


def log_info(message):
    print(message)
    if not isinstance(message, str):
        message = json.dumps(message)
    logging.info(message)


def log_warning(message):
    print(message)
    if not isinstance(message, str):
        message = json.dumps(message)
    logging.warning(message)


def log_error(message):
    print(message)
    if not isinstance(message, str):
        message = json.dumps(message)
    logging.error(message)


def log_exception(message):
    print(message)
    if not isinstance(message, str):
        message = json.dumps(message)
    logging.exception(message)


# Initialize the logger.
logging.basicConfig(filename=config.DEFAULT_LOG_FILE + '.log', level=logging.INFO)


class ResourceManagerCore(Observable):

    def __init__(self, instance_id, account_id):
        super().__init__()
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
            log_error("You should add the AmazonS3ReadOnlyAccess and AmazonS3FullAccess "
                      "permission to the user")
            return None

    def create_bucket(self, bucket_name):
        """
        Method called to create a bucket.
        """
        if self.s3_resource.Bucket(bucket_name).creation_date is None:
            current_region = self.s3_session.region_name
            log_info("Creating bucket with bucket_name: " + bucket_name + ".")
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
            print("Bucket {} does not exist, so it cannot be deleted.".format(bucket_name))
        else:
            log_info("Deleting bucket with bucket_name: " + bucket_name)
            bucket = self.s3_resource.Bucket(bucket_name)
            bucket.object_versions.delete()
            log_info("Deleted bucket " + bucket_name)
            self.s3.delete_bucket(Bucket=bucket_name)

    def upload_file(self, file_path, key, bucket_name):
        """
        Method called to upload a file with path 'file_path' to the bucket with
        name 'bucket_name' and upload it to the storage with name 'key'.
        :param file_path: Path of the file to be uploaded.
        :param key: Name of the key to upload to.
        :param bucket_name: The name of the bucket to upload to.
        """
        start_time = time()
        if self.s3_resource.Bucket(bucket_name).creation_date is None:
            print("Bucket " + bucket_name + " does not exist, so a file cannot be uploaded to this bucket.")
        else:
            try:
                print("Uploading file to bucket {}: {} with {}".format(bucket_name, file_path, key))
                self.s3.upload_file(file_path, bucket_name, key)
            except DataNotFoundError:
                print("There is no file with file_path {}, so the file cannot be uploaded.".format(file_path))
            except ClientError as exc:
                print("There was a ClientError during uploading to S3: {}".format(exc))
            except Exception as exc:
                print("Could not upload file due to exception {}: {}".format(exc, traceback.print_exc()))
        log_metric({'upload_duration': time() - start_time})

    def download_file(self, bucket_name, key, file_path):
        """
        Method called to download from the bucket with name 'bucket_name' and
        key 'key' and download it to the file with path 'file_path'.
        :param bucket_name: Name of the bucket to download the file from.
        :param key: Name of the key to download from.
        :param file_path: Path of the file to download to.
        """
        start_time = time()
        if not bucket_name:
            error_message = "Could not download file with key: {}, as the bucket permissions are wrong!".format(key)
            print(error_message)
            raise FileNotFoundError(error_message)
        if self.s3_resource.Bucket(bucket_name).creation_date is None:
            print("Bucket " + bucket_name + " does not exist, so a file cannot be downloaded from it.")
        else:
            try:
                self.s3.download_file(bucket_name, key, file_path)
                log_info("Downloading file {} from the bucket {}.".format(file_path, bucket_name))
            except DataNotFoundError:
                log_error(
                    "There is no key {} in bucket {} so a file cannot be downloaded from it.".format(key, bucket_name))
        log_metric({'download_duration': time() - start_time})

    def upload_log(self, clean, im=False):
        try:
            temporary_copy = config.DEFAULT_LOG_FILE + '_copy.log'
            shutil.copy(config.DEFAULT_LOG_FILE + '.log', temporary_copy)
            if clean:  # If clean, do not keep the log.
                if not im:
                    os.remove(config.DEFAULT_LOG_FILE + '.log')
            else:  # If not clean, clear the original.
                open(config.DEFAULT_LOG_FILE + '.log', 'w').close()
            key = '{}_{}.log'.format(self._instance_id,
                                     datetime.now(timezone('Europe/Amsterdam')).strftime('%Y%m%d%H%M%S'))
            self.upload_file(file_path=temporary_copy, key=key,
                             bucket_name=(self.account_id + '-logging'))
            if not im:
                os.remove(temporary_copy)
        except FileNotFoundError:
            print("There were no more logs to report to S3. Temporary.log was not found.")
        except Exception as exc:
            print("Could not upload logs to S3 due to {} with: {}".format(exc, traceback.print_exc()))

    async def period_upload_log(self):
        while True:
            self.upload_log(clean=False)
            await asyncio.sleep(config.LOGGING_INTERVAL)
