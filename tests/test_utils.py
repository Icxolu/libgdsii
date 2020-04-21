import unittest
import random

import libgdsii.utils as utils


class TestEightByteRealConversion(unittest.TestCase):

    def test_eight_byte_real_to_float(self):
        data = b'>A\x897K\xc6\xa7\xf0'
        value = utils.eight_byte_real_to_float(data)
        self.assertEqual(value, 0.001)

    def test_float_to_eight_byte_real(self):
        value = 0.001
        data = utils.float_to_eight_byte_real(value)
        self.assertEqual(data, b'>A\x897K\xc6\xa7\xf0')

    def test_conversion_random(self):
        start_value = random.uniform(-1, 1)
        end_value = utils.eight_byte_real_to_float(utils.float_to_eight_byte_real(start_value))
        self.assertEqual(start_value, end_value)