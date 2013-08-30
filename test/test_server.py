#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from mock import MagicMock, Mock, patch, call
import os
from uiautomator import AutomatorServer


class TestAutomatorServer(unittest.TestCase):

    def test_device_serial(self):
        serial = "76HDGKDN783HD6D"
        with patch("uiautomator.adb") as adb:
            adb.devices = {serial: "device"}
            with patch.dict('os.environ', {}, clear=True):
                self.assertEqual(AutomatorServer().device_serial(), serial)
                self.assertTrue("ANDROID_SERIAL" in os.environ)
                self.assertEqual(os.environ["ANDROID_SERIAL"], serial)
            with patch.dict('os.environ', {"ANDROID_SERIAL": "XXX"}):
                self.assertEqual(AutomatorServer().device_serial(), "XXX")
            adb.devices = {}
            with self.assertRaises(EnvironmentError):
                AutomatorServer().device_serial()
            adb.devices = {serial: "device", "AAA": "device2"}
            with patch.dict('os.environ', {}, clear=True):
                with self.assertRaises(EnvironmentError):
                    AutomatorServer().device_serial()
            with patch.dict('os.environ', {"ANDROID_SERIAL": "XXX"}):
                with self.assertRaises(EnvironmentError):
                    AutomatorServer().device_serial()
            with patch.dict('os.environ', {"ANDROID_SERIAL": serial}):
                self.assertEqual(AutomatorServer().device_serial(), serial)
                self.assertTrue("ANDROID_SERIAL" in os.environ)
                self.assertEqual(os.environ["ANDROID_SERIAL"], serial)

    def test_local_port(self):
        serial = "76HDGKDN783HD6D"
        with patch("uiautomator.adb") as adb:
            server = AutomatorServer()
            server.device_serial = MagicMock()
            server.device_serial.return_value = serial
            adb.forward_list = {serial: [9009, 9001], "xxx": [123, 9001]}
            self.assertEqual(server.local_port, 9009)
            adb.forward_list = {"aaa": [9009, 9001], "xxx": [123, 9001]}
            self.assertEqual(server.local_port, 9009)  # the second time will retrieve the stored one.

            server = AutomatorServer()
            server.device_serial = MagicMock()
            server.device_serial.return_value = serial
            adb.forward_list = {"aaa": [9009, 9001], "xxx": [123, 9001]}
            self.assertEqual(server.local_port, None)

    def test_start_success(self):
        serial = "76HDGKDN783HD6D"
        with patch("uiautomator.adb") as adb:
            with patch("uiautomator.server_port") as server_port:
                server = AutomatorServer()
                server.device_serial = MagicMock()
                server.device_serial.return_value = serial
                adb.forward_list = {"a": [9008, 9008], "b": [9009, 9008]}
                server_port.return_value = 9000
                adb.forward.return_value = 0
                server.ping = MagicMock()
                server.ping.return_value = "pong"
                server.start()
                adb.forward.assert_called_once_with(9010, 9000)

    def test_start_forward_error(self):
        serial = "76HDGKDN783HD6D"
        with patch("uiautomator.adb") as adb:
            with patch("uiautomator.server_port") as server_port:
                server = AutomatorServer()
                server.device_serial = MagicMock()
                server.device_serial.return_value = serial
                adb.forward_list = {"a": [9008, 9008], "b": [9009, 9008]}
                server_port.return_value = 9000
                adb.forward.return_value = 1
                with self.assertRaises(IOError):
                    server.start()
                assert adb.forward.call_count == 190

    def test_start_error(self):
        serial = "76HDGKDN783HD6D"
        with patch("uiautomator.adb") as adb:
            with patch("uiautomator.server_port") as server_port:
                server = AutomatorServer()
                server.device_serial = MagicMock()
                server.device_serial.return_value = serial
                adb.forward_list = {"a": [9008, 9008], "b": [9009, 9008]}
                server_port.return_value = 9000
                adb.forward.return_value = 0
                server.ping = MagicMock()
                server.ping.return_value = None
                with self.assertRaises(IOError):
                    server.start()
                adb.forward.assert_called_once_with(9010, 9000)

    def test_auto_start(self):
        serial = "76HDGKDN783HD6D"
        with patch("uiautomator.adb") as adb:
            with patch("uiautomator.server_port") as server_port:
                with patch("uiautomator.JsonRPCClient") as JsonRPCClient:
                    server = AutomatorServer()
                    server.device_serial = MagicMock()
                    server.device_serial.return_value = serial
                    adb.forward_list = {serial: [9008, 9000]}
                    server_port.return_value = 9000
                    results = [None, "pong"]

                    def side_effect(*args):
                        result = results.pop(0)
                        return result
                    server.ping = Mock(side_effect=side_effect)
                    server.start = MagicMock()
                    server.jsonrpc
                    JsonRPCClient.assert_called_once_with(server.rpc_uri)
                    server.start.assert_called_once_with()
                    server.jsonrpc  # second call will retrieve the stored obj
                    JsonRPCClient.assert_called_once_with(server.rpc_uri)
                    server.start.assert_called_once_with()

    def test_stop(self):
        result = "USER     PID   PPID  VSIZE  RSS     WCHAN    PC         NAME%ssystem    372   126   635596 104808 ffffffff 00000000 S uiautomator"
        returns = [result % "\n\r", result % "\r\n", result % "\r", result % "\n"]
        for r in returns:
            with patch("uiautomator.adb") as adb:
                adb.cmd.return_value.communicate.return_value = (r, "")
                server = AutomatorServer()
                server.stop()
                self.assertEqual(adb.cmd.call_args_list,
                                 [call("shell", "ps", "-C", "uiautomator"), call("shell", "kill", "-9", "372")])
