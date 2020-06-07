import json
import unittest
from aws.utils.botoutils import BotoInstanceReader


class TestBotoIntanceReader(unittest.TestCase):

    def test_simple_run(self):
        with open('test_files/boto_result.json') as file:
            boto_result = file.readlines()
            boto_result = json.loads(''.join(boto_result))
            boto_instances = BotoInstanceReader(region_name='eu-central-1').read(
                own_instance='i-0c785590248a26fa6',
                boto_response=boto_result)
            print('No filter: {}'.format(boto_instances))

    def test_simple_run_filter(self):
        with open('test_files/boto_result.json') as file:
            boto_result = file.readlines()
            boto_result = json.loads(''.join(boto_result))
            boto_instances = BotoInstanceReader(region_name='eu-central-1').read(
                own_instance='i-0c785590248a26fa6',
                filters=['is_node_manager'],
                boto_response=boto_result)
            print('Node managers: {}'.format(boto_instances))

    def test_is_running(self):
        with open('test_files/boto_result.json') as file:
            boto_result = file.readlines()
            boto_result = json.loads(''.join(boto_result))
            boto_instances = BotoInstanceReader(region_name='eu-central-1').read(
                own_instance='i-0c785590248a26fa6',
                filters=['is_node_manager', 'is_running'],
                boto_response=boto_result)
            print('Started: {}'.format(boto_instances))

    def test_not_running_NM(self):
        with open('test_files/boto_result.json') as file:
            boto_result = file.readlines()
            boto_result = json.loads(''.join(boto_result))
            boto_instances = BotoInstanceReader(region_name='eu-central-1').read(
                own_instance='i-0c785590248a26fa6',
                filters=['is_node_manager',
                         ('is_running', False)],
                boto_response=boto_result)
            print('Not Started NM: {}'.format(boto_instances))

    def test_not_running(self):
        with open('test_files/boto_result.json') as file:
            boto_result = file.readlines()
            boto_result = json.loads(''.join(boto_result))
            boto_instances = BotoInstanceReader(region_name='eu-central-1').read(
                own_instance='i-0c785590248a26fa6',
                filters=[('is_running', False)],
                boto_response=boto_result)
            print('Not Started: {}'.format(boto_instances))

    def test_workers(self):
        with open('test_files/boto_result.json') as file:
            boto_result = file.readlines()
            boto_result = json.loads(''.join(boto_result))
            boto_instances = BotoInstanceReader(region_name='eu-central-1').read(
                own_instance='i-0c785590248a26fa6',
                filters=['is_worker'],
                boto_response=boto_result)
            print('Workers: {}'.format(boto_instances))


if __name__ == '__main__':
    unittest.main()
