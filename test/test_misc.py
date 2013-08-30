#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import uiautomator


class TestMisc(unittest.TestCase):

    def test_load(self):
        reload(uiautomator)
        self.assertIsNotNone(uiautomator.device)
        self.assertIsNotNone(uiautomator.rect)
        self.assertIsNotNone(uiautomator.point)
