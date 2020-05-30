import unittest
from aws.utils.botoutils import BotoInstanceReader


class TestBotoIntanceReader(unittest.TestCase):

    def test_upper(self):
        with open('test_files/boto_result.json') as file:
            boto_result = file.readlines()
            boto_result = ''.join(boto_result)
            boto_instances = BotoInstanceReader.read(boto_result)
            print(str(boto_instances))
            self.assertEqual('foo'.upper(), 'FOO')


if __name__ == '__main__':
    unittest.main()