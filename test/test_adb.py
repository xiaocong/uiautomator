#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from mock import MagicMock, patch
import os
from uiautomator import Adb


class TestAdb(unittest.TestCase):

    def test_adb_from_env(self):
        home_dir = '/android/home'
        with patch.dict('os.environ', {'ANDROID_HOME': home_dir}):
            with patch('os.path.exists') as exists:
                exists.return_value = True

                os.name = "posix"  # linux
                adb_obj = Adb()
                adb_path = os.path.join(home_dir, "platform-tools", "adb")
                self.assertEqual(adb_obj.adb, adb_path)
                exists.assert_called_once_with(adb_path)
                self.assertEqual(adb_obj.adb, adb_path)
                exists.assert_called_once_with(adb_path) # the second call will return the __adb_cmd directly

                os.name = "nt"  # linux
                adb_obj = Adb()
                adb_path = os.path.join(home_dir, "platform-tools", "adb.exe")
                self.assertEqual(adb_obj.adb, adb_path)

                exists.return_value = False
                with self.assertRaises(EnvironmentError):
                    Adb().adb

    def test_adb_from_find(self):
        with patch.dict('os.environ', {}, clear=True):
            with patch("distutils.spawn.find_executable") as find_executable:
                find_executable.return_value = "/usr/bin/adb"
                with patch("os.path.realpath") as realpath:
                    realpath.return_value = "/home/user/android/platform-tools/adb"
                    self.assertEqual(realpath.return_value, Adb().adb)
                    find_executable.assert_called_once_with("adb")  # find_exectable should be called once
                    realpath.assert_called_once_with(find_executable.return_value)
                    realpath.return_value = find_executable.return_value
                    self.assertEqual(find_executable.return_value, Adb().adb)
                find_executable.return_value = None
                call_count = find_executable.call_count
                with self.assertRaises(EnvironmentError):
                    Adb().adb
                self.assertEqual(call_count + 1, find_executable.call_count)

    def test_devices(self):
        adb = Adb()
        adb.cmd = MagicMock()
        adb.cmd.return_value.communicate.return_value = (b"List of devices attached \r\n014E05DE0F02000E    device\r\n489328DKFL7DF    device", b"")
        self.assertEqual(adb.devices, {"014E05DE0F02000E": "device", "489328DKFL7DF": "device"})
        adb.cmd.assert_called_once_with("devices")
        adb.cmd.return_value.communicate.return_value = (b"List of devices attached \n\r014E05DE0F02000E    device\n\r489328DKFL7DF    device", b"")
        self.assertEqual(adb.devices, {"014E05DE0F02000E": "device", "489328DKFL7DF": "device"})
        adb.cmd.return_value.communicate.return_value = (b"List of devices attached \r014E05DE0F02000E    device\r489328DKFL7DF    device", b"")
        self.assertEqual(adb.devices, {"014E05DE0F02000E": "device", "489328DKFL7DF": "device"})
        adb.cmd.return_value.communicate.return_value = (b"List of devices attached \n014E05DE0F02000E    device\n489328DKFL7DF    device", b"")
        self.assertEqual(adb.devices, {"014E05DE0F02000E": "device", "489328DKFL7DF": "device"})
        adb.cmd.return_value.communicate.return_value = (b"not match", "")
        with self.assertRaises(EnvironmentError):
            adb.devices

    def test_forward(self):
        adb = Adb()
        adb.cmd = MagicMock()
        adb.forward(90, 91)
        adb.cmd.assert_called_once_with("forward", "tcp:90", "tcp:91")
        adb.cmd.return_value.wait.assert_called_once_with()

    def test_forward_list(self):
        adb = Adb()
        with patch("uiautomator.server_port") as server_port:
            server_port.return_value = 9000
            adb.cmd = MagicMock()
            adb.cmd.return_value.communicate.return_value = (b"014E05DE0F02000E tcp:9008 tcp:9000\r\n387GDB7HDJ73G\ttcp:9009\ttcp:9000\n\r365GDB7HDJHDGF\ttcp:9009\ttcp:9008", b"")
            self.assertEqual(adb.forward_list, {"014E05DE0F02000E": [9008, 9000], "387GDB7HDJ73G": [9009, 9000]})
            adb.cmd.assert_called_once_with("forward", "--list")
            adb.cmd.return_value.communicate.return_value = (b"014E05DE0F02000E tcp:9008 tcp:9000\n387GDB7HDJ73G\ttcp:9009\ttcp:9000\r365GDB7HDJHDGF\ttcp:9009\ttcp:9008", b"")
            self.assertEqual(adb.forward_list, {"014E05DE0F02000E": [9008, 9000], "387GDB7HDJ73G": [9009, 9000]})

    def test_adb_cmd(self):
        home_dir = '/android/home'
        with patch.dict('os.environ', {'ANDROID_HOME': home_dir}):
            with patch('os.path.exists') as exists:
                exists.return_value = True
                import subprocess
                with patch("subprocess.Popen") as Popen:
                    adb = Adb()
                    args = ["a", "b", "c"]
                    adb.cmd(*args)
                    Popen.assert_called_once_with(["%s %s" % (adb.adb, " ".join(args))], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
