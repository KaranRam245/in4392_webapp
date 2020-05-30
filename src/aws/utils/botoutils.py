import json


class BotoInstanceReader:

    @staticmethod
    def read(boto_response):
        boto_response = json.loads(boto_response)['Reservations']
        boto_instances = []
        for reserverations in boto_response:
            json_instance = reserverations['Instances'][0]
            boto_instance = BotoInstance.instance(json_instance)
            boto_instances.append(boto_instance)
        return boto_instances


class BotoInstance:

    @staticmethod
    def instance(content):
        return BotoInstance(**content)

    def __init__(self, InstanceId, PublicDnsName, State, Tags, **kwargs):
        self.instance_id = InstanceId
        self.dns = PublicDnsName
        self.state = State['Name']
        self.tags = Tags

    def __str__(self) -> str:
        return "BotoInstance[instance_id: {}, dns: {}, state: {}, tags: {}]".format(
            self.instance_id, self.dns, self.state, self.tags)

    def __repr__(self):
        return self.__str__()
