"""
Module for the Resource Manager.
"""
import sys
sys.path.append('./src')

from aws.utils.monitor import Listener
from S3Connector import S3Connector
import uuid


class ResourceManagerCore:

    def __init__(self):
        self.S3 = S3Connector()

    def run(self):
        self.create_bucket()
        print(self.S3.get_bucket_list())

    def create_bucket(self):
        """
        Method called to create a bucket.
        """
        bucket_name = str(uuid.uuid4())
        bucket_response = self.S3.create_bucket(
            bucket_name)
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
