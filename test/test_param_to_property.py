#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from uiautomator import param_to_property


class TestParamToProperty(unittest.TestCase):

    def test_props(self):
        args_value = None
        kwargs_value = None

        @param_to_property("one", "two", "three")
        def func(*args, **kwargs):
            self.assertEqual(args, args_value)
            self.assertEqual(kwargs, kwargs_value)

        args_value = ("one", "two", "three")
        kwargs_value = {"test": 1}
        func.one.two.three(test=1)
        args_value = ("one", "three")
        kwargs_value = {"another_test": 100}
        func.one("three", another_test=100)
        args_value = ("one", "two", "three")
        kwargs_value = {}
        func("one", "two", "three")
        args_value = ("three", "one", "two")
        kwargs_value = {}
        func.three("one", "two")

    def test_kwprops(self):
        args_value = None
        kwargs_value = None

        @param_to_property(key=["one", "two", "three"])
        def func(*args, **kwargs):
            self.assertEqual(args, args_value)
            self.assertEqual(kwargs, kwargs_value)

        args_value = (1,)
        kwargs_value = {"key": "one"}
        func.one(1)
        args_value = (2, 3)
        kwargs_value = {"key": "two"}
        func.two(2, 3)
        args_value = ()
        kwargs_value = {}
        func()

    def test_error(self):
        @param_to_property(key=["one", "two", "three"])
        def func(*args, **kwargs):
            pass

        with self.assertRaises(AttributeError):
            func.one.one

        with self.assertRaises(SyntaxError):
            @param_to_property("a", "b", key=["one", "two", "three"])
            def func(*args, **kwargs):
                pass
