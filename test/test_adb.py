#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from mock import MagicMock, patch
import os
from uiautomator import Adb


class TestAdb(unittest.TestCase):

    def setUp(self):
        self.os_name = os.name

    def tearDown(self):
        os.name = self.os_name


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
                exists.assert_called_once_with(adb_path) # the second call will return the __adb_cmd directly

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
        adb.raw_cmd.return_value.communicate.return_value = (b"List of devices attached \r\n014E05DE0F02000E    device\r\n489328DKFL7DF    device", b"")
        self.assertEqual(adb.devices(), {"014E05DE0F02000E": "device", "489328DKFL7DF": "device"})
        adb.raw_cmd.assert_called_once_with("devices")
        adb.raw_cmd.return_value.communicate.return_value = (b"List of devices attached \n\r014E05DE0F02000E    device\n\r489328DKFL7DF    device", b"")
        self.assertEqual(adb.devices(), {"014E05DE0F02000E": "device", "489328DKFL7DF": "device"})
        adb.raw_cmd.return_value.communicate.return_value = (b"List of devices attached \r014E05DE0F02000E    device\r489328DKFL7DF    device", b"")
        self.assertEqual(adb.devices(), {"014E05DE0F02000E": "device", "489328DKFL7DF": "device"})
        adb.raw_cmd.return_value.communicate.return_value = (b"List of devices attached \n014E05DE0F02000E    device\n489328DKFL7DF    device", b"")
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
        adb.raw_cmd.assert_called_once_with("-s", adb.device_serial(), *args)

    def test_device_serial(self):
        adb = Adb()
        adb.devices = MagicMock()
        adb.devices.return_value = {"ABCDEF123456": "device"}
        with patch.dict('os.environ', {'ANDROID_SERIAL': "ABCDEF123456"}):
            self.assertEqual(adb.device_serial(), "ABCDEF123456")
        adb.devices.return_value = {"ABCDEF123456": "device", "123456ABCDEF": "device"}
        with patch.dict('os.environ', {'ANDROID_SERIAL': "ABCDEF123456"}):
            self.assertEqual(adb.device_serial(), "ABCDEF123456")
        adb.devices.return_value = {"ABCDEF123456": "device", "123456ABCDEF": "device"}
        with patch.dict('os.environ', {'ANDROID_SERIAL': "HIJKLMN098765"}):
            with self.assertRaises(EnvironmentError):
                adb.device_serial()
        adb.devices.return_value = {"ABCDEF123456": "device", "123456ABCDEF": "device"}
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(EnvironmentError):
                adb.device_serial()
        adb.devices.return_value = {"ABCDEF123456": "device"}
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(adb.device_serial(), "ABCDEF123456")

        adb.devices.return_value = {}
        with self.assertRaises(EnvironmentError):
            adb.device_serial()
