"""
Module for the Resource Manager.
"""
import sys
sys.path.append('./src')

from aws.utils.monitor import Listener
import uuid
import boto3
from botocore.exceptions import ClientError


class ResourceManagerCore:

    def __init__(self):
        self.S3 = boto3.client('s3')

    def run(self):
        try:
            self.create_bucket()
        except ClientError:
            print("You should add the AmazonS3ReadOnlyAccess permission to the user")
        print(self.S3.list_buckets())

    def create_bucket(self):
        """
        Method called to create a bucket.
        """
        bucket_name = str(uuid.uuid4())
        print(bucket_name)
        bucket_response = self.S3.create_bucket(
            Bucket=bucket_name)
        print(bucket_name)
        return bucket_name, bucket_response

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
