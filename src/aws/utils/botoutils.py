import boto3

from aws.utils.state import InstanceState


class BotoInstanceReader:

    def __init__(self, region_name=None):
        sess = boto3.session.Session()
        if region_name:
            self.ec2 = sess.client('ec2', region_name=region_name)
            self.ssm = sess.client('ssm', region_name=region_name)
        else:
            self.ec2 = sess.client('ec2')
            self.ssm = sess.client('ssm')

    def read_ids(self, own_instance, filters=None, boto_response: dict = None):
        output = self.read(own_instance, filters, boto_response=boto_response)
        return [inst.instance_id for inst in output]

    def read(self, own_instance, filters=None, boto_response: dict = None):
        """
        Read the boto response of ec2 describe-instance and convert to a list of
        BotoInstances.
        :param own_instance: The instance_id of the instance manager.
        :param filters: Any filters if wanted. E.g., `is-running`.
        :param boto_response: A dict containing the boto3 describe-instances response.
        :return: List of BotoInstances.
        """
        if filters is None:
            filters = []
        if not boto_response:
            boto_response = self.ec2.describe_instances()
        boto_instances = []
        for reserverations in boto_response['Reservations']:
            json_instance = reserverations['Instances'][0]
            boto_instance = BotoInstance.instance(json_instance)
            # Remove the Instance Manager and if the filter_out option wants it.
            if boto_instance.instance_id != own_instance and not BotoInstanceReader._filter_out(
                    boto_instance, filters):
                boto_instances.append(boto_instance)
        return boto_instances

    @staticmethod
    def _filter_out(instance, filters):
        if filters:
            for func in filters:
                if isinstance(func, tuple) and not getattr(instance, func[0])() == func[1]:
                    return True
                if isinstance(func, str) and not getattr(instance, func)():
                    return True
        return False


class BotoInstance:

    @staticmethod
    def instance(content):
        print(content)
        return BotoInstance(**content)

    def __init__(self, InstanceId, PublicDnsName, PublicIpAddress, State, Tags, **kwargs):
        self.instance_id = InstanceId
        self.dns = PublicDnsName
        self.public_ip = PublicIpAddress
        self.state = InstanceState(State['Name'])
        self.name = ''
        for tag in Tags:
            if tag['Key'] == 'Name':
                self.name = self.map_name(tag['Value'])
                break

    def __str__(self) -> str:
        name = self.name if self.name != '' else 'BotoInstance'
        return "{}[instance_id: {}, dns: {}, state: {}]".format(
            name, self.instance_id, self.dns, self.state)

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def map_name(name: str):
        return name.lower().replace(' ', '_')

    def is_running(self) -> bool:
        return self.state == 'running'

    def is_worker(self) -> bool:
        return self.name == 'worker'

    def is_instance_manger(self) -> bool:
        return self.name == 'instance_manager'

    def is_node_manager(self) -> bool:
        return self.name == 'node_manager'
