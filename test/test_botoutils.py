import unittest
from aws.utils.botoutils import BotoInstanceReader


class TestBotoIntanceReader(unittest.TestCase):

    def test_simple_run(self):
        with open('test_files/boto_result.json') as file:
            boto_result = file.readlines()
            boto_result = ''.join(boto_result)
            boto_instances = BotoInstanceReader.read(boto_result, 'i-0c785590248a26fa6')
            print('No filter: {}'.format(boto_instances))

    def test_simple_run_filter(self):
        with open('test_files/boto_result.json') as file:
            boto_result = file.readlines()
            boto_result = ''.join(boto_result)
            boto_instances = BotoInstanceReader.read(boto_result, 'i-0c785590248a26fa6',
                                                     filters=['is_node_manager'])
            print('Node managers: {}'.format(boto_instances))

    def test_is_running(self):
        with open('test_files/boto_result.json') as file:
            boto_result = file.readlines()
            boto_result = ''.join(boto_result)
            boto_instances = BotoInstanceReader.read(boto_result, 'i-0c785590248a26fa6',
                                                     filters=['is_node_manager', 'is_running'])
            print('Started: {}'.format(boto_instances))

    def test_not_running(self):
        with open('test_files/boto_result.json') as file:
            boto_result = file.readlines()
            boto_result = ''.join(boto_result)
            boto_instances = BotoInstanceReader.read(boto_result, 'i-0c785590248a26fa6',
                                                     filters=['is_node_manager',
                                                              ('is_running', False)])
            print('Not Started: {}'.format(boto_instances))


if __name__ == '__main__':
    unittest.main()
