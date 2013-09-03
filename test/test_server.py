#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from mock import MagicMock, Mock, patch, call, mock_open
import os
from uiautomator import AutomatorServer


class TestAutomatorServer(unittest.TestCase):

    def test_local_port(self):
        for port in range(9000, 9100):
            with patch.dict('os.environ', {'LOCAL_PORT': str(port)}):
                self.assertEqual(AutomatorServer().local_port, port)
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(AutomatorServer().local_port, 9008)

    def test_device_port(self):
        for port in range(9000, 9100):
            with patch.dict('os.environ', {'DEVICE_PORT': str(port)}):
                self.assertEqual(AutomatorServer().device_port, port)
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(AutomatorServer().device_port, 9008)

    def test_start_success(self):
        server = AutomatorServer()
        server.download_and_push = MagicMock()
        server.download_and_push.return_value = ["bundle.jar", "uiautomator-stub.jar"]
        server.ping = MagicMock()
        server.ping.return_value = "pong"
        with patch("uiautomator.adb") as adb:
            adb.forward.return_value = 0
            with patch.dict('os.environ', {'LOCAL_PORT': '9000', 'DEVICE_PORT': '9000'}):
                server.start()
                adb.cmd.assert_valled_onec_with('shell', 'uiautomator', 'runtest', 'bundle.jar', 'uiautomator-stub.jar', '-c', 'com.github.uiautomatorstub.Stub')
                adb.forward.assert_called_once_with(9000, 9000)

    def test_start_forward_error(self):
        server = AutomatorServer()
        server.download_and_push = MagicMock()
        server.download_and_push.return_value = ["bundle.jar", "uiautomator-stub.jar"]
        with patch("uiautomator.adb") as adb:
            adb.forward.return_value = 1
            with patch.dict('os.environ', {'LOCAL_PORT': '9000', 'DEVICE_PORT': '9000'}):
                with self.assertRaises(IOError):
                    server.start()
                adb.forward.assert_called_once_with(9000, 9000)

    def test_start_error(self):
        server = AutomatorServer()
        server.download_and_push = MagicMock()
        server.download_and_push.return_value = ["bundle.jar", "uiautomator-stub.jar"]
        server.ping = MagicMock()
        server.ping.return_value = None
        with patch("uiautomator.adb") as adb:
            adb.forward.return_value = 0
            with patch.dict('os.environ', {'LOCAL_PORT': '9000', 'DEVICE_PORT': '9000'}):
                with patch("time.sleep"):
                    with self.assertRaises(IOError):
                        server.start()
                adb.forward.assert_called_once_with(9000, 9000)

    def test_auto_start(self):
        with patch.dict('os.environ', {'LOCAL_PORT': '9000', 'DEVICE_PORT': '9000'}):
            with patch("uiautomator.JsonRPCClient") as JsonRPCClient:
                JsonRPCClient.ping.return_value = None
                server = AutomatorServer()
                server.start = MagicMock()
                server.jsonrpc
                JsonRPCClient.assert_called_once_with(server.rpc_uri)
                server.start.assert_called_once_with()
                server.jsonrpc  # second call will retrieve the stored obj
                JsonRPCClient.assert_called_once_with(server.rpc_uri)

    def test_start_ping(self):
        with patch.dict('os.environ', {'LOCAL_PORT': '9000', 'DEVICE_PORT': '9000'}):
            with patch("uiautomator.JsonRPCClient") as JsonRPCClient:
                JsonRPCClient.return_value.ping.return_value = "pong"
                server = AutomatorServer()
                self.assertEqual(server.ping(), "pong")

    def test_start_ping_none(self):
        with patch.dict('os.environ', {'LOCAL_PORT': '9000', 'DEVICE_PORT': '9000'}):
            with patch("uiautomator.JsonRPCClient") as JsonRPCClient:
                JsonRPCClient.return_value.ping.side_effect = Exception("error")
                server = AutomatorServer()
                self.assertEqual(server.ping(), None)


class TestAutomatorServer_Stop(unittest.TestCase):

    def setUp(self):
        try:
            import urllib2
            self.urlopen_patch = patch('urllib2.urlopen')
        except:
            self.urlopen_patch = patch('urllib.request.urlopen')
        finally:
            self.urlopen = self.urlopen_patch.start()

    def tearDown(self):
        self.urlopen_patch.stop()

    @patch("uiautomator.adb")
    def test_download_and_push(self, adb):
        jars = ["bundle.jar", "uiautomator-stub.jar"]
        with patch("os.path.exists") as exists:
            server = AutomatorServer()
            exists.return_value = True
            self.assertEqual(set(server.download_and_push()), set(jars))
            for args in adb.cmd.call_args_list:
                self.assertEqual(args[0][0], "push")
                self.assertEqual(args[0][2], "/data/local/tmp/")

    @patch("uiautomator.adb")
    def test_download_and_push_download(self, adb):
        jars = ["bundle.jar", "uiautomator-stub.jar"]
        with patch("os.path.exists") as exists,\
             patch("os.mkdir") as mkdir,\
             patch("%s.open" % open.__class__.__module__, mock_open(), create=True) as m_open:
            server = AutomatorServer()
            exists.return_value = False
            self.assertEqual(set(server.download_and_push()), set(jars))
            self.assertEqual(len(m_open.call_args_list), len(jars))

    @patch("uiautomator.adb")
    def test_stop_started_server(self, adb):
        serial = "76HDGKDN783HD6D"
        server = AutomatorServer()
        server.uiautomator_process = process = MagicMock()
        process.poll.return_value = None
        server.stop()
        process.wait.assert_called_once_with()

        server.uiautomator_process = process = MagicMock()
        process.poll.return_value = None
        self.urlopen.side_effect = IOError("error")
        server.stop()
        process.kill.assert_called_once_with()

    def test_stop(self):
        results = [
            b"USER     PID   PPID  VSIZE  RSS     WCHAN    PC         NAME\n\rsystem    372   126   635596 104808 ffffffff 00000000 S uiautomator",
            b"USER     PID   PPID  VSIZE  RSS     WCHAN    PC         NAME\r\nsystem    372   126   635596 104808 ffffffff 00000000 S uiautomator",
            b"USER     PID   PPID  VSIZE  RSS     WCHAN    PC         NAME\nsystem    372   126   635596 104808 ffffffff 00000000 S uiautomator",
            b"USER     PID   PPID  VSIZE  RSS     WCHAN    PC         NAME\rsystem    372   126   635596 104808 ffffffff 00000000 S uiautomator"
        ]
        for r in results:
            with patch("uiautomator.adb") as adb:
                adb.cmd.return_value.communicate.return_value = (r, "")
                server = AutomatorServer()
                server.stop()
                self.assertEqual(adb.cmd.call_args_list,
                                 [call("shell", "ps", "-C", "uiautomator"), call("shell", "kill", "-9", "372")])
