"""
Module for the Resource Manager.
"""
from aws.utils.monitor import Listener
from S3Connector import S3Connector


class ResourceManagerCore:

    def __init__(self):
        pass

    def run(self):
        raise NotImplementedError()


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

class S3Connector(self, key_id,access_key,aws_reg,conf):

    def __init__(self):
        self.S3 = S3Connector(
            # aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
            # aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
            # aws_region=os.environ['AWS_REGION']
        )

    def run(self):
        raise NotImplementedError()