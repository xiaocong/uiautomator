#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import re
import os.path
import codecs
from mock import MagicMock, call, patch
from uiautomator import AutomatorDevice, Selector


class TestDevice(unittest.TestCase):

    def setUp(self):
        self.device = AutomatorDevice()
        self.device.server = MagicMock()
        self.device.server.jsonrpc = MagicMock()
        self.device.server.jsonrpc_wrap = MagicMock()

    def test_info(self):
        self.device.server.jsonrpc.deviceInfo = MagicMock()
        self.device.server.jsonrpc.deviceInfo.return_value = {}
        self.assertEqual(self.device.info, {})
        self.device.server.jsonrpc.deviceInfo.assert_called_once_with()

    def test_click(self):
        self.device.server.jsonrpc.click = MagicMock()
        self.device.server.jsonrpc.click.return_value = True
        self.assertEqual(self.device.click(1, 2), True)
        self.device.server.jsonrpc.click.assert_called_once_with(1, 2)

    def test_swipe(self):
        self.device.server.jsonrpc.swipe = MagicMock()
        self.device.server.jsonrpc.swipe.return_value = True
        self.assertEqual(self.device.swipe(1, 2, 3, 4, 100), True)
        self.device.server.jsonrpc.swipe.assert_called_once_with(1, 2, 3, 4, 100)

    def test_long_click(self):
        self.device.server.jsonrpc.swipe = MagicMock()
        self.device.server.jsonrpc.swipe.return_value = True
        x, y = 100, 200
        self.assertEqual(self.device.long_click(x, y), True)
        self.device.server.jsonrpc.swipe.assert_called_once_with(x, y, x+1, y+1, 100)

    def test_drag(self):
        self.device.server.jsonrpc.drag = MagicMock()
        self.device.server.jsonrpc.drag.return_value = True
        self.assertEqual(self.device.drag(1, 2, 3, 4, 100), True)
        self.device.server.jsonrpc.drag.assert_called_once_with(1, 2, 3, 4, 100)

    def test_dump(self):
        self.device.server.jsonrpc.dumpWindowHierarchy = MagicMock()
        with codecs.open(os.path.join(os.path.dirname(__file__), "res", "layout.xml"), "r", encoding="utf8") as f:
            xml = f.read()
            self.device.server.jsonrpc.dumpWindowHierarchy.return_value = xml
            self.assertEqual(self.device.dump("/tmp/test.xml"), xml)
            self.device.server.jsonrpc.dumpWindowHierarchy.assert_called_once_with(True, None)
            self.assertEqual(self.device.dump("/tmp/test.xml", False), xml)

            raw_xml = "".join(re.split(r"\n[ ]*", xml))
            self.device.server.jsonrpc.dumpWindowHierarchy.return_value = raw_xml
            self.assertTrue("\n  " in self.device.dump("/tmp/test.xml"))

    def test_screenshot(self):
        self.device.server.jsonrpc.takeScreenshot = MagicMock()
        self.device.server.jsonrpc.takeScreenshot.return_value = "1.png"
        self.device.server.adb.cmd = cmd = MagicMock()
        self.device.server.screenshot = MagicMock()
        self.device.server.screenshot.return_value = None
        cmd.return_value.returncode = 0
        self.assertEqual(self.device.screenshot("a.png", 1.0, 99), "a.png")
        self.device.server.jsonrpc.takeScreenshot.assert_called_once_with("screenshot.png", 1.0, 99)
        self.assertEqual(cmd.call_args_list, [call("pull", "1.png", "a.png"), call("shell", "rm", "1.png")])

        self.device.server.jsonrpc.takeScreenshot.return_value = None
        self.assertEqual(self.device.screenshot("a.png", 1.0, 100), None)

    def test_freeze_rotation(self):
        self.device.server.jsonrpc.freezeRotation = MagicMock()
        self.device.freeze_rotation(True)
        self.device.freeze_rotation(False)
        self.assertEqual(self.device.server.jsonrpc.freezeRotation.call_args_list, [call(True), call(False)])

    def test_orientation(self):
        self.device.server.jsonrpc.deviceInfo = MagicMock()
        orientation = {
            0: "natural",
            1: "left",
            2: "upsidedown",
            3: "right"
        }
        for i in range(4):
            self.device.server.jsonrpc.deviceInfo.return_value = {"displayRotation": i}
            self.assertEqual(self.device.orientation, orientation[i])
        # set
        orientations = [
            (0, "natural", "n", 0),
            (1, "left", "l", 90),
            (2, "upsidedown", "u", 180),
            (3, "right", "r", 270)
        ]
        for values in orientations:
            for value in values:
                self.device.server.jsonrpc.setOrientation = MagicMock()
                self.device.orientation = value
                self.device.server.jsonrpc.setOrientation.assert_called_once_with(values[1])

        with self.assertRaises(ValueError):
            self.device.orientation = "invalid orientation"

    def test_last_traversed_text(self):
        self.device.server.jsonrpc.getLastTraversedText = MagicMock()
        self.device.server.jsonrpc.getLastTraversedText.return_value = "abcdef"
        self.assertEqual(self.device.last_traversed_text, "abcdef")
        self.device.server.jsonrpc.getLastTraversedText.assert_called_once_with()

    def test_clear_traversed_text(self):
        self.device.server.jsonrpc.clearLastTraversedText = MagicMock()
        self.device.clear_traversed_text()
        self.device.server.jsonrpc.clearLastTraversedText.assert_called_once_with()

    def test_open(self):
        self.device.server.jsonrpc.openNotification = MagicMock()
        self.device.open.notification()
        self.device.server.jsonrpc.openNotification.assert_called_once_with()
        self.device.server.jsonrpc.openQuickSettings = MagicMock()
        self.device.open.quick_settings()
        self.device.server.jsonrpc.openQuickSettings.assert_called_once_with()

    def test_watchers(self):
        names = ["a", "b", "c"]
        self.device.server.jsonrpc.getWatchers = MagicMock()
        self.device.server.jsonrpc.getWatchers.return_value = names
        self.assertEqual(self.device.watchers, names)
        self.device.server.jsonrpc.getWatchers.assert_called_once_with()

        self.device.server.jsonrpc.hasAnyWatcherTriggered = MagicMock()
        self.device.server.jsonrpc.hasAnyWatcherTriggered.return_value = True
        self.assertEqual(self.device.watchers.triggered, True)
        self.device.server.jsonrpc.hasAnyWatcherTriggered.assert_called_once_with()

        self.device.server.jsonrpc.removeWatcher = MagicMock()
        self.device.watchers.remove("a")
        self.device.server.jsonrpc.removeWatcher.assert_called_once_with("a")
        self.device.server.jsonrpc.removeWatcher = MagicMock()
        self.device.watchers.remove()
        self.assertEqual(self.device.server.jsonrpc.removeWatcher.call_args_list, [call(name) for name in names])

        self.device.server.jsonrpc.resetWatcherTriggers = MagicMock()
        self.device.watchers.reset()
        self.device.server.jsonrpc.resetWatcherTriggers.assert_called_once_with()

        self.device.server.jsonrpc.runWatchers = MagicMock()
        self.device.watchers.run()
        self.device.server.jsonrpc.runWatchers.assert_called_once_with()

    def test_watcher(self):
        self.device.server.jsonrpc.hasWatcherTriggered = MagicMock()
        self.device.server.jsonrpc.hasWatcherTriggered.return_value = False
        self.assertFalse(self.device.watcher("name").triggered)
        self.device.server.jsonrpc.hasWatcherTriggered.assert_called_once_with("name")

        self.device.server.jsonrpc.removeWatcher = MagicMock()
        self.device.watcher("a").remove()
        self.device.server.jsonrpc.removeWatcher.assert_called_once_with("a")

        self.device.server.jsonrpc.registerClickUiObjectWatcher = MagicMock()
        condition1 = {"text": "my text", "className": "android"}
        condition2 = {"description": "my desc", "clickable": True}
        target = {"className": "android.widget.Button", "text": "OK"}
        self.device.watcher("watcher").when(**condition1).when(**condition2).click(**target)
        self.device.server.jsonrpc.registerClickUiObjectWatcher.assert_called_once_with(
            "watcher",
            [Selector(**condition1), Selector(**condition2)],
            Selector(**target)
        )

        self.device.server.jsonrpc.registerPressKeyskWatcher = MagicMock()
        self.device.watcher("watcher2").when(**condition1).when(**condition2).press.back.home.power("menu")
        self.device.server.jsonrpc.registerPressKeyskWatcher.assert_called_once_with(
            "watcher2", [Selector(**condition1), Selector(**condition2)], ("back", "home", "power", "menu"))

    def test_press(self):
        key = ["home", "back", "left", "right", "up", "down", "center",
               "menu", "search", "enter", "delete", "del", "recent",
               "volume_up", "volume_down", "volume_mute", "camera", "power"]
        self.device.server.jsonrpc.pressKey = MagicMock()
        self.device.server.jsonrpc.pressKey.return_value = True
        self.assertTrue(self.device.press.home())
        self.device.server.jsonrpc.pressKey.return_value = False
        self.assertFalse(self.device.press.back())
        self.device.server.jsonrpc.pressKey.return_value = False
        for k in key:
            self.assertFalse(self.device.press(k))
        self.assertEqual(self.device.server.jsonrpc.pressKey.call_args_list, [call("home"), call("back")] + [call(k) for k in key])

        self.device.server.jsonrpc.pressKeyCode.return_value = True
        self.assertTrue(self.device.press(1))
        self.assertTrue(self.device.press(1, 2))
        self.assertEqual(self.device.server.jsonrpc.pressKeyCode.call_args_list, [call(1), call(1, 2)])

    def test_wakeup(self):
        self.device.server.jsonrpc.wakeUp = MagicMock()
        self.device.wakeup()
        self.device.server.jsonrpc.wakeUp.assert_called_once_with()

        self.device.server.jsonrpc.wakeUp = MagicMock()
        self.device.screen.on()
        self.device.server.jsonrpc.wakeUp.assert_called_once_with()

        self.device.server.jsonrpc.wakeUp = MagicMock()
        self.device.screen("on")
        self.device.server.jsonrpc.wakeUp.assert_called_once_with()

    def test_screen_status(self):
        self.device.server.jsonrpc.deviceInfo = MagicMock()
        self.device.server.jsonrpc.deviceInfo.return_value = {"screenOn": True}
        self.assertTrue(self.device.screen == "on")
        self.assertTrue(self.device.screen != "off")

        self.device.server.jsonrpc.deviceInfo.return_value = {"screenOn": False}
        self.assertTrue(self.device.screen == "off")
        self.assertTrue(self.device.screen != "on")

    def test_sleep(self):
        self.device.server.jsonrpc.sleep = MagicMock()
        self.device.sleep()
        self.device.server.jsonrpc.sleep.assert_called_once_with()

        self.device.server.jsonrpc.sleep = MagicMock()
        self.device.screen.off()
        self.device.server.jsonrpc.sleep.assert_called_once_with()

        self.device.server.jsonrpc.sleep = MagicMock()
        self.device.screen("off")
        self.device.server.jsonrpc.sleep.assert_called_once_with()

    def test_wait_idle(self):
        self.device.server.jsonrpc_wrap.return_value.waitForIdle = MagicMock()
        self.device.server.jsonrpc_wrap.return_value.waitForIdle.return_value = True
        self.assertTrue(self.device.wait.idle(timeout=10))
        self.device.server.jsonrpc_wrap.return_value.waitForIdle.assert_called_once_with(10)

        self.device.server.jsonrpc_wrap.return_value.waitForIdle = MagicMock()
        self.device.server.jsonrpc_wrap.return_value.waitForIdle.return_value = False
        self.assertFalse(self.device.wait("idle", timeout=10))
        self.device.server.jsonrpc_wrap.return_value.waitForIdle.assert_called_once_with(10)

    def test_wait_update(self):
        self.device.server.jsonrpc_wrap.return_value.waitForWindowUpdate = MagicMock()
        self.device.server.jsonrpc_wrap.return_value.waitForWindowUpdate.return_value = True
        self.assertTrue(self.device.wait.update(timeout=10, package_name="android"))
        self.device.server.jsonrpc_wrap.return_value.waitForWindowUpdate.assert_called_once_with("android", 10)

        self.device.server.jsonrpc_wrap.return_value.waitForWindowUpdate = MagicMock()
        self.device.server.jsonrpc_wrap.return_value.waitForWindowUpdate.return_value = False
        self.assertFalse(self.device.wait("update", timeout=100, package_name="android"))
        self.device.server.jsonrpc_wrap.return_value.waitForWindowUpdate.assert_called_once_with("android", 100)

    def test_get_info_attr(self):
        info = {"test_a": 1, "test_b": "string", "displayWidth": 720, "displayHeight": 1024}
        self.device.server.jsonrpc.deviceInfo = MagicMock()
        self.device.server.jsonrpc.deviceInfo.return_value = info
        for k in info:
            self.assertEqual(getattr(self.device, k), info[k])
        self.assertEqual(self.device.width, info["displayWidth"])
        self.assertEqual(self.device.height, info["displayHeight"])
        with self.assertRaises(AttributeError):
            self.device.not_exists

    def test_device_obj(self):
        with patch("uiautomator.AutomatorDeviceObject") as AutomatorDeviceObject:
            kwargs = {"text": "abc", "description": "description...", "clickable": True}
            self.device(**kwargs)
            AutomatorDeviceObject.assert_called_once_with(self.device, Selector(**kwargs))

        with patch("uiautomator.AutomatorDeviceObject") as AutomatorDeviceObject:
            AutomatorDeviceObject.return_value.exists = True
            self.assertTrue(self.device.exists(clickable=True))
            AutomatorDeviceObject.return_value.exists = False
            self.assertFalse(self.device.exists(text="..."))


class TestDeviceWithSerial(unittest.TestCase):

    def test_serial(self):
        with patch('uiautomator.AutomatorServer') as AutomatorServer:
            AutomatorDevice("abcdefhijklmn")
            AutomatorServer.assert_called_once_with(serial="abcdefhijklmn", local_port=None, adb_server_host=None, adb_server_port=None)
