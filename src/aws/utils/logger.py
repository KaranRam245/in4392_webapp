"""
Module for the logger.
"""
import aws.utils.config as config
from aws.resourcemanager.resourcemanager import ResourceManagerCore
from aws_logging_handlers.S3 import S3Handler
import logging



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
        resource_manager = ResourceManagerCore()
        self.logger = logging.getLogger('root')
        resource_manager.create_bucket(bucket_name=config.LOGGING_BUCKET_NAME)
        s3_handler = S3Handler("test_log", config.LOGGING_BUCKET_NAME, workers=1)
        self.logger.addHandler(s3_handler)

    def log_info(self, instance_id: str, message):
        self.logger.info(message)
        self.add_handler(instance_id)

    def log_error(self, instance_id: str, message):
        self.logger.error(message)
        self.add_handler(instance_id)

    def log_exception(self, instance_id: str, message):
        self.logger.exception(message)
        self.add_handler(instance_id)

    def add_handler(self, type, instance_id):
        s3_handler = S3Handler(instance_id, config.LOGGING_BUCKET_NAME, workers=1)
        self.logger.addHandler(s3_handler)