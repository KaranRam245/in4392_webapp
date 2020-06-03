

class BotoInstanceReader:

    @staticmethod
    def read_ids(ec2, own_instance, filters=None):
        output = BotoInstanceReader.read(own_instance, filters)
        return [inst.instance_id for inst in output]

    @staticmethod
    def read(ec2, own_instance, filters=None):
        if filters is None:
            filters = []
        boto_response = ec2.describe_instances()
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
        return BotoInstance(**content)

    def __init__(self, InstanceId, PublicDnsName, State, Tags, **kwargs):
        self.instance_id = InstanceId
        self.dns = PublicDnsName
        self.state = State['Name']
        self.tags = Tags
        self.name = ''
        for tag in self.tags:
            if tag['Key'] == 'Name':
                self.name = self.map_name(tag['Value'])
                break

    def __str__(self) -> str:
        name = self.name if self.name != '' else 'BotoInstance'
        return "{}[instance_id: {}, dns: {}, state: {}, tags: {}]".format(
            name, self.instance_id, self.dns, self.state, self.tags)

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def map_name(name: str):
        return name.lower().replace('_', ' ')

    def is_running(self) -> bool:
        return self.state == 'running'

    def is_worker(self) -> bool:
        return self.name == 'Worker'

    def is_instance_manger(self) -> bool:
        return self.name == 'Instance Manager'

    def is_node_manager(self) -> bool:
        return self.name == 'Node Manager'

    def is_resource_manager(self) -> bool:
        return self.name == 'Resource Manager'
