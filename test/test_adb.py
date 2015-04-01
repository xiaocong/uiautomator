#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from mock import MagicMock, patch
import os
import subprocess
from uiautomator import Adb


class TestAdb(unittest.TestCase):

    def setUp(self):
        self.os_name = os.name

    def tearDown(self):
        os.name = self.os_name

    def test_serial(self):
        serial = "abcdef1234567890"
        adb = Adb(serial)
        self.assertEqual(adb.default_serial, serial)

        adb.devices = MagicMock()
        adb.devices.return_value = [serial, "123456"]
        self.assertEqual(adb.device_serial(), serial)

    def test_adb_from_env(self):
        home_dir = '/android/home'
        with patch.dict('os.environ', {'ANDROID_HOME': home_dir}):
            with patch('os.path.exists') as exists:
                exists.return_value = True

                os.name = "posix"  # linux
                adb_obj = Adb()
                adb_path = os.path.join(home_dir, "platform-tools", "adb")
                self.assertEqual(adb_obj.adb(), adb_path)
                exists.assert_called_once_with(adb_path)
                self.assertEqual(adb_obj.adb(), adb_path)
                # the second call will return the __adb_cmd directly
                exists.assert_called_once_with(adb_path)

                os.name = "nt"  # linux
                adb_obj = Adb()
                adb_path = os.path.join(home_dir, "platform-tools", "adb.exe")
                self.assertEqual(adb_obj.adb(), adb_path)

                exists.return_value = False
                with self.assertRaises(EnvironmentError):
                    Adb().adb()

    def test_adb_from_find(self):
        with patch.dict('os.environ', {}, clear=True):
            with patch("distutils.spawn.find_executable") as find_executable:
                find_executable.return_value = "/usr/bin/adb"
                with patch("os.path.realpath") as realpath:
                    realpath.return_value = "/home/user/android/platform-tools/adb"
                    self.assertEqual(realpath.return_value, Adb().adb())
                    find_executable.assert_called_once_with("adb")  # find_exectable should be called once
                    realpath.assert_called_once_with(find_executable.return_value)
                    realpath.return_value = find_executable.return_value
                    self.assertEqual(find_executable.return_value, Adb().adb())
                find_executable.return_value = None
                call_count = find_executable.call_count
                with self.assertRaises(EnvironmentError):
                    Adb().adb()
                self.assertEqual(call_count + 1, find_executable.call_count)

    def test_devices(self):
        adb = Adb()
        adb.raw_cmd = MagicMock()
        adb.raw_cmd.return_value.communicate.return_value = (b"List of devices attached \r\n014E05DE0F02000E\tdevice\r\n489328DKFL7DF\tdevice", b"")
        self.assertEqual(adb.devices(), {"014E05DE0F02000E": "device", "489328DKFL7DF": "device"})
        adb.raw_cmd.assert_called_once_with("devices")
        adb.raw_cmd.return_value.communicate.return_value = (b"List of devices attached \n\r014E05DE0F02000E\tdevice\n\r489328DKFL7DF\tdevice", b"")
        self.assertEqual(adb.devices(), {"014E05DE0F02000E": "device", "489328DKFL7DF": "device"})
        adb.raw_cmd.return_value.communicate.return_value = (b"List of devices attached \r014E05DE0F02000E\tdevice\r489328DKFL7DF\tdevice", b"")
        self.assertEqual(adb.devices(), {"014E05DE0F02000E": "device", "489328DKFL7DF": "device"})
        adb.raw_cmd.return_value.communicate.return_value = (b"List of devices attached \n014E05DE0F02000E\tdevice\n489328DKFL7DF\tdevice", b"")
        self.assertEqual(adb.devices(), {"014E05DE0F02000E": "device", "489328DKFL7DF": "device"})
        adb.raw_cmd.return_value.communicate.return_value = (b"not match", "")
        with self.assertRaises(EnvironmentError):
            adb.devices()

    def test_forward(self):
        adb = Adb()
        adb.cmd = MagicMock()
        adb.forward(90, 91)
        adb.cmd.assert_called_once_with("forward", "tcp:90", "tcp:91")
        adb.cmd.return_value.wait.assert_called_once_with()

    def test_adb_raw_cmd(self):
        import subprocess
        adb = Adb()
        adb.adb = MagicMock()
        adb.adb.return_value = "adb"
        args = ["a", "b", "c"]
        with patch("subprocess.Popen") as Popen:
            os.name = "posix"
            adb.raw_cmd(*args)
            Popen.assert_called_once_with(["%s %s" % (adb.adb(), " ".join(args))], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with patch("subprocess.Popen") as Popen:
            os.name = "nt"
            adb.raw_cmd(*args)
            Popen.assert_called_once_with([adb.adb()] + list(args), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_adb_cmd(self):
        adb = Adb()
        adb.device_serial = MagicMock()
        adb.device_serial.return_value = "ANDROID_SERIAL"
        adb.raw_cmd = MagicMock()
        args = ["a", "b", "c"]
        adb.cmd(*args)
        adb.raw_cmd.assert_called_once_with("-s", "%s" % adb.device_serial(), *args)

        adb.device_serial.return_value = "ANDROID SERIAL"
        adb.raw_cmd = MagicMock()
        args = ["a", "b", "c"]
        adb.cmd(*args)
        adb.raw_cmd.assert_called_once_with("-s", "'%s'" % adb.device_serial(), *args)

    def test_adb_cmd_server_host(self):
        adb = Adb(adb_server_host="localhost", adb_server_port=5037)
        adb.adb = MagicMock()
        adb.adb.return_value = "adb"
        adb.device_serial = MagicMock()
        adb.device_serial.return_value = "ANDROID_SERIAL"
        args = ["a", "b", "c"]
        with patch("subprocess.Popen") as Popen:
            os.name = "nt"
            adb.raw_cmd(*args)
            Popen.assert_called_once_with(
                [adb.adb()] + args,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

        adb = Adb(adb_server_host="test.com", adb_server_port=1000)
        adb.adb = MagicMock()
        adb.adb.return_value = "adb"
        adb.device_serial = MagicMock()
        adb.device_serial.return_value = "ANDROID_SERIAL"
        args = ["a", "b", "c"]
        with patch("subprocess.Popen") as Popen:
            os.name = "posix"
            adb.raw_cmd(*args)
            Popen.assert_called_once_with(
                [" ".join([adb.adb()] + ["-H", "test.com", "-P", "1000"] + args)],
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

    def test_device_serial(self):
        with patch.dict('os.environ', {'ANDROID_SERIAL': "ABCDEF123456"}):
            adb = Adb()
            adb.devices = MagicMock()
            adb.devices.return_value = {"ABCDEF123456": "device"}
            self.assertEqual(adb.device_serial(), "ABCDEF123456")
        with patch.dict('os.environ', {'ANDROID_SERIAL': "ABCDEF123456"}):
            adb = Adb()
            adb.devices = MagicMock()
            adb.devices.return_value = {"ABCDEF123456": "device", "123456ABCDEF": "device"}
            self.assertEqual(adb.device_serial(), "ABCDEF123456")
        with patch.dict('os.environ', {'ANDROID_SERIAL': "HIJKLMN098765"}):
            adb = Adb()
            adb.devices = MagicMock()
            adb.devices.return_value = {"ABCDEF123456": "device", "123456ABCDEF": "device"}
            self.assertEqual(adb.device_serial(), "HIJKLMN098765")
        with patch.dict('os.environ', {}, clear=True):
            adb = Adb()
            adb.devices = MagicMock()
            adb.devices.return_value = {"ABCDEF123456": "device", "123456ABCDEF": "device"}
            with self.assertRaises(EnvironmentError):
                adb.device_serial()
        with patch.dict('os.environ', {}, clear=True):
            adb = Adb()
            adb.devices = MagicMock()
            adb.devices.return_value = {"ABCDEF123456": "device"}
            self.assertEqual(adb.device_serial(), "ABCDEF123456")

        with self.assertRaises(EnvironmentError):
            adb = Adb()
            adb.devices = MagicMock()
            adb.devices.return_value = {}
            adb.device_serial()

    def test_forward_list(self):
        adb = Adb()
        adb.version = MagicMock()
        adb.version.return_value = ['1.0.31', '1', '0', '31']
        adb.raw_cmd = MagicMock()
        adb.raw_cmd.return_value.communicate.return_value = (b"014E05DE0F02000E    tcp:9008    tcp:9008\r\n489328DKFL7DF    tcp:9008    tcp:9008", b"")
        self.assertEqual(adb.forward_list(), [['014E05DE0F02000E', 'tcp:9008', 'tcp:9008'], ['489328DKFL7DF', 'tcp:9008', 'tcp:9008']])

        adb.version.return_value = ['1.0.29', '1', '0', '29']
        with self.assertRaises(EnvironmentError):
            adb.forward_list()
