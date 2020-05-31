import json


class BotoInstanceReader:

    @staticmethod
    def read(boto_response, own_instance):
        boto_response = json.loads(boto_response)['Reservations']
        boto_instances = []
        for reserverations in boto_response:
            json_instance = reserverations['Instances'][0]
            boto_instance = BotoInstance.instance(json_instance)
            if boto_instance.instance_id != own_instance:  # Remove the Instance Manager.
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
        self.name = ''
        for tag in self.tags:
            if tag['Key'] == 'Name':
                self.name = tag['Value']
                break

    def __str__(self) -> str:
        name = self.name if self.name != '' else 'BotoInstance'
        return "{}[instance_id: {}, dns: {}, state: {}, tags: {}]".format(
            name, self.instance_id, self.dns, self.state, self.tags)

    def __repr__(self):
        return self.__str__()
