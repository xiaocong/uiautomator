#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import uiautomator
import os
from mock import patch


class TestMisc(unittest.TestCase):

    def test_proxy(self):
        self.assertTrue('no_proxy' in os.environ)
        self.assertTrue('localhost' in os.environ.get('no_proxy', ''))

    def test_load(self):
        try:
            from imp import reload
        except:
            pass
        reload(uiautomator)
        self.assertIsNotNone(uiautomator.device)
        self.assertIsNotNone(uiautomator.rect)
        self.assertIsNotNone(uiautomator.point)

    def test_rect(self):
        import random
        for i in range(10):
            top, left = random.randint(0, 100), random.randint(0, 100)
            bottom, right = random.randint(101, 1024), random.randint(101, 720)
            self.assertEqual(uiautomator.rect(top, left, bottom, right), {"top": top, "left": left, "bottom": bottom, "right": right})

    def test_point(self):
        import random
        for i in range(10):
            x, y = random.randint(0, 1024), random.randint(0, 720)
            self.assertEqual(uiautomator.point(x, y), {"x": x, "y": y})

    def test_next_port(self):
        with patch('socket.socket') as socket:
            socket.return_value.connect_ex.side_effect = [0, 0, 1]
            uiautomator._init_local_port = 9007
            self.assertEqual(uiautomator.next_local_port(), 9010)

        with patch('socket.socket') as socket:
            socket.return_value.connect_ex.return_value = 1
            uiautomator._init_local_port = 32764
            self.assertEqual(uiautomator.next_local_port(), 9008)
