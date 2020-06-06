"""
Module for the Resource Manager.
"""
from aws.utils.monitor import Listener
import uuid
import boto3
from botocore.exceptions import ClientError, DataNotFoundError
import os


class ResourceManagerCore:

    def __init__(self):
        self.S3 = boto3.client('s3')
        self.S3_resource = boto3.resource('s3')
        self.S3_Session = boto3.session.Session()

    def run(self):
        try:
            # Check the bucket list
            bucket_list = self.S3.list_buckets()["Buckets"]
            # If there are no buckets, create a new one
            if not bucket_list:
                name,response = self.create_bucket()
                bucket_list = self.S3.list_buckets()["Buckets"]
            # Use the first bucket in the list
            bucket_name = bucket_list[0]["Name"]
            """
            Lines below is an example of what you can do with this code.
            """
            key = 'text'
            if os.path.exists('src/aws/resourcemanager/upload.txt'):
                self.upload_file('src/aws/resourcemanager/upload.txt',
                    bucket_name, key)
                self.download_file(bucket_name, key,
                    'src/aws/resourcemanager/download.txt')
        except ClientError:
            print("You should add the AmazonS3ReadOnlyAccess and AmazonS3FullAccess permission to the user")
        print(self.S3.list_buckets())

    def create_bucket(self):
        """
        Method called to create a bucket.
        """
        bucket_name = str(uuid.uuid4())
        current_region = self.S3_Session.region_name
        bucket_response = self.S3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={
                'LocationConstraint': current_region,
            }
        )
        return bucket_name, bucket_response

    def delete_bucket(self, bucket_name):
        """
        Method called to delete the bucket with the name 'bucket_name'.
        :param bucket_name: Name of the bucket to be deleted.
        """
        if self.S3_resource.Bucket(bucket_name).creation_date is None:
            print("Bucket " + bucket_name + " does not exist")
        else:
            bucket = self.S3_resource.Bucket(bucket_name)
            bucket.object_versions.delete()
            self.S3.delete_bucket(Bucket=bucket_name)

    def upload_file(self, file_path, bucket_name, key):
        """
        Method called to upload a file with path 'file_path' to the bucket with
        name 'bucket_name' and upload it to the storage with name 'key'.
        :param file_path: Path of the file to be uploaded.
        :param bucket_name: Name of the bucket to upload the file to.
        :param key: Name of the key to upload to.
        """
        if self.S3_resource.Bucket(bucket_name).creation_date is None:
            print("Bucket " + bucket_name + " does not exist")
        else:
            try:
                self.S3.upload_file(file_path, bucket_name, key)
            except DataNotFoundError:
                print("There is no file with file_path " +
                sys.path + " + " + file_path)

    def download_file(self, bucket_name, key, file_path):
        """
        Method called to download from the bucket with name 'bucket_name' and
        key 'key' and download it to the file with path 'file_path'.
        :param bucket_name: Name of the bucket to download the file from.
        :param key: Name of the key to download from.
        :param file_path: Path of the file to download to.
        """
        if self.S3_resource.Bucket(bucket_name).creation_date is None:
            print("Bucket " + bucket_name + " does not exist")
        else:
            try:
                self.S3.download_file(bucket_name, key, file_path)
            except DataNotFoundError:
                print("There is no key " + key + " in bucket " + bucket_name)


class ResourceMonitor(Listener):

    def __init__(self):
        pass

    def event(self, message):
        """
        Method called when the notify function is called in the Observable class. The Listener is
        notified through the event function with a dict message result.
        :param message: Message of the event in dict format.
        """
        raise NotImplementedError("The class is a listener but has not implemented the event "
                                  "method.")


if __name__ == "__main__":
    ResourceManagerCore().run()
