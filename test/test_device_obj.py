#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from mock import MagicMock, call, patch
from uiautomator import AutomatorDeviceObject, Selector


class TestDeviceObjInit(unittest.TestCase):

    def setUp(self):
        self.device = MagicMock()
        self.device.server.jsonrpc = MagicMock()

    def test_init(self):
        kwargs = {"text": "text", "className": "android"}
        self.device_obj = AutomatorDeviceObject(self.device,
                                                **kwargs)
        self.assertEqual(self.device_obj.selector,
                         Selector(**kwargs))
        self.assertEqual(self.device_obj.jsonrpc,
                         self.device.server.jsonrpc)


class TestDeviceObj(unittest.TestCase):

    def setUp(self):
        self.device = MagicMock()
        self.jsonrpc = self.device.server.jsonrpc = MagicMock()
        self.kwargs = {"text": "text", "className": "android"}
        self.obj = AutomatorDeviceObject(self.device,
                                         **self.kwargs)

    def test_child_selector(self):
        kwargs = {"text": "child text", "className": "android"}
        self.obj.child_selector(**kwargs)
        self.assertEqual(self.obj.selector["childSelector"],
                         Selector(**kwargs))

    def test_from_parent(self):
        kwargs = {"text": "parent text", "className": "android"}
        self.obj.from_parent(**kwargs)
        self.assertEqual(self.obj.selector["fromParent"],
                         Selector(**kwargs))

    def test_exists(self):
        self.jsonrpc.exist = MagicMock()
        self.jsonrpc.exist.return_value = True
        self.assertTrue(self.obj.exists)

        self.jsonrpc.exist.return_value = False
        self.assertFalse(self.obj.exists)

        self.assertEqual(self.jsonrpc.exist.call_args_list,
                         [call(self.obj.selector),
                          call(self.obj.selector)])

    def test_info(self):
        info = {"text": "item text"}
        self.jsonrpc.objInfo.return_value = info
        self.assertEqual(self.obj.info,
                         info)
        self.jsonrpc.objInfo.assert_called_once_with(self.obj.selector)

    def test_info_attr(self):
        info = {u'contentDescription': u'',
                u'checked': False,
                u'scrollable': False,
                u'text': u'',
                u'packageName': u'android',
                u'selected': False,
                u'enabled': True,
                u'bounds': {u'top': 0,
                            u'left': 0,
                            u'right': 720,
                            u'bottom': 1184},
                u'className':
                u'android.widget.FrameLayout',
                u'focusable': False,
                u'focused': False,
                u'clickable': False,
                u'checkable': False,
                u'chileCount': 2,
                u'longClickable': False,
                u'visibleBounds': {u'top': 0,
                                   u'left': 0,
                                   u'right': 720,
                                   u'bottom': 1184}}
        self.jsonrpc.objInfo.return_value = info
        self.assertEqual(self.obj.info, info)
        self.jsonrpc.objInfo.assert_called_once_with(self.obj.selector)
        self.assertEqual(self.obj.description, info["contentDescription"])

    def test_text(self):
        self.jsonrpc.clearTextField = MagicMock()
        self.obj.set_text(None)
        self.obj.set_text("")
        self.obj.clear_text()
        self.assertEqual(self.jsonrpc.clearTextField.call_args_list,
                         [call(self.obj.selector), call(self.obj.selector), call(self.obj.selector)])

        self.jsonrpc.setText.return_value = False
        texts = ["abc", "123", "()#*$&"]
        for text in texts:
            self.assertFalse(self.obj.set_text(text))
        self.assertEqual(self.jsonrpc.setText.call_args_list,
                         [call(self.obj.selector, t) for t in texts])

    def test_click(self):
        self.jsonrpc.click.return_value = False
        corners = ["tl", "topleft", "br", "bottomright"]
        for c in corners:
            self.assertFalse(self.obj.click(c))
        self.assertEqual(self.jsonrpc.click.call_args_list,
                         [call(self.obj.selector, c) for c in corners])

        self.jsonrpc.click = MagicMock()
        self.jsonrpc.click.return_value = True
        corners = ["tl", "topleft", "br", "bottomright"]
        for c in corners:
            self.assertTrue(getattr(self.obj.click, c)())
        self.assertEqual(self.jsonrpc.click.call_args_list,
                         [call(self.obj.selector, c) for c in corners])

        self.jsonrpc.click = MagicMock()
        self.jsonrpc.click.return_value = True
        self.assertTrue(self.obj.click())
        self.jsonrpc.click.assert_called_once_with(self.obj.selector)

    def test_click_wait(self):
        self.jsonrpc.clickAndWaitForNewWindow.return_value = True
        self.assertTrue(self.obj.click.wait(timeout=321))
        self.jsonrpc.clickAndWaitForNewWindow.assert_called_once_with(self.obj.selector, 321)

    def test_long_click(self):
        self.jsonrpc.longClick.return_value = False
        corners = ["tl", "topleft", "br", "bottomright"]
        for c in corners:
            self.assertFalse(self.obj.long_click(c))
        self.assertEqual(self.jsonrpc.longClick.call_args_list,
                         [call(self.obj.selector, c) for c in corners])

        self.jsonrpc.longClick = MagicMock()
        self.jsonrpc.longClick.return_value = True
        corners = ["tl", "topleft", "br", "bottomright"]
        for c in corners:
            self.assertTrue(getattr(self.obj.long_click, c)())
        self.assertEqual(self.jsonrpc.longClick.call_args_list,
                         [call(self.obj.selector, c) for c in corners])

        self.jsonrpc.longClick = MagicMock()
        self.jsonrpc.longClick.return_value = True
        self.assertTrue(self.obj.long_click())
        self.jsonrpc.longClick.assert_called_once_with(self.obj.selector)

    def test_drag_to(self):
        self.jsonrpc.dragTo.return_value = False
        self.assertFalse(self.obj.drag.to(10, 20, steps=10))
        self.jsonrpc.dragTo.return_value = True
        self.assertTrue(self.obj.drag.to(x=10, y=20, steps=20))

        sel = {"text": "text..."}
        self.assertTrue(self.obj.drag.to(steps=30, **sel))
        self.assertEqual(self.jsonrpc.dragTo.call_args_list,
                         [call(self.obj.selector, 10, 20, 10),
                          call(self.obj.selector, 10, 20, 20),
                          call(self.obj.selector, Selector(**sel), 30)])

    def test_gesture(self):
        self.jsonrpc.gesture.return_value = True
        self.assertTrue(self.obj.gesture(1, 2, 3, 4, 100))
        self.assertTrue(self.obj.gesture(4, 3).to(2, 1, 20))
        self.assertEqual(self.jsonrpc.gesture.call_args_list,
                         [call(self.obj.selector, 1, 2, 3, 4, 100), call(self.obj.selector, 4, 3, 2, 1, 20)])

    def test_pinch(self):
        self.jsonrpc.pinchIn.return_value = True
        self.assertTrue(self.obj.pinch.In(percent=90, steps=30))
        self.assertTrue(self.obj.pinch("in", 80, 40))
        self.assertTrue(self.obj.pinch("In", 70, 50))
        self.assertEqual(self.jsonrpc.pinchIn.call_args_list,
                         [call(self.obj.selector, 90, 30), call(self.obj.selector, 80, 40), call(self.obj.selector, 70, 50)])

        self.jsonrpc.pinchOut.return_value = True
        self.assertTrue(self.obj.pinch.Out(percent=90, steps=30))
        self.assertTrue(self.obj.pinch("out", 80, 40))
        self.assertTrue(self.obj.pinch("Out", 70, 50))
        self.assertEqual(self.jsonrpc.pinchIn.call_args_list,
                         [call(self.obj.selector, 90, 30), call(self.obj.selector, 80, 40), call(self.obj.selector, 70, 50)])

    def test_swipe(self):
        self.jsonrpc.swipe.return_value = True
        dirs = ["up", "down", "right", "left"]
        for d in dirs:
            self.assertTrue(self.obj.swipe(d, 30))
        self.assertEqual(self.jsonrpc.swipe.call_args_list,
                         [call(self.obj.selector, d, 30) for d in dirs])

        self.jsonrpc.swipe = MagicMock()
        self.jsonrpc.swipe.return_value = True
        dirs = ["up", "down", "right", "left"]
        for d in dirs:
            self.assertTrue(getattr(self.obj.swipe, d)(steps=30))
        self.assertEqual(self.jsonrpc.swipe.call_args_list,
                         [call(self.obj.selector, d, 30) for d in dirs])

    def test_fling(self):
        self.jsonrpc.flingForward.return_value = True
        self.assertTrue(self.obj.fling.horiz.forward())
        self.assertTrue(self.obj.fling.horizentally.forward())
        self.assertTrue(self.obj.fling.vert.forward())
        self.assertTrue(self.obj.fling())
        self.assertEqual(self.jsonrpc.flingForward.call_args_list,
                         [call(self.obj.selector, False), call(self.obj.selector, False), call(self.obj.selector, True), call(self.obj.selector, True)])
        
        self.jsonrpc.flingBackward.return_value = True
        self.assertTrue(self.obj.fling.horiz.backward())
        self.assertTrue(self.obj.fling.horizentally.backward())
        self.assertTrue(self.obj.fling.vert.backward())
        self.assertTrue(self.obj.fling.vertically.backward())
        self.assertEqual(self.jsonrpc.flingBackward.call_args_list,
                         [call(self.obj.selector, False), call(self.obj.selector, False), call(self.obj.selector, True), call(self.obj.selector, True)])
        
        max_swipes = 1000
        self.jsonrpc.flingToBeginning.return_value = True
        self.assertTrue(self.obj.fling.horiz.toBeginning())
        self.assertTrue(self.obj.fling.horizentally.toBeginning())
        self.assertTrue(self.obj.fling.vert.toBeginning())
        self.assertTrue(self.obj.fling.vertically.toBeginning(max_swipes=100))
        self.assertEqual(self.jsonrpc.flingToBeginning.call_args_list,
                         [call(self.obj.selector, False, max_swipes), call(self.obj.selector, False, max_swipes), call(self.obj.selector, True, max_swipes), call(self.obj.selector, True, 100)])
        self.jsonrpc.flingToEnd.return_value = True
        self.assertTrue(self.obj.fling.horiz.toEnd())
        self.assertTrue(self.obj.fling.horizentally.toEnd())
        self.assertTrue(self.obj.fling.vert.toEnd())
        self.assertTrue(self.obj.fling.vertically.toEnd(max_swipes=100))
        self.assertEqual(self.jsonrpc.flingToEnd.call_args_list,
                         [call(self.obj.selector, False, max_swipes), call(self.obj.selector, False, max_swipes), call(self.obj.selector, True, max_swipes), call(self.obj.selector, True, 100)])

    def test_scroll(self):
        steps = 100
        max_swipes = 1000
        self.jsonrpc.scrollForward.return_value = True
        self.assertTrue(self.obj.scroll.horiz.forward())
        self.assertTrue(self.obj.scroll.horizentally.forward())
        self.assertTrue(self.obj.scroll.vert.forward())
        self.assertTrue(self.obj.scroll(steps=20))
        self.assertEqual(self.jsonrpc.scrollForward.call_args_list,
                         [call(self.obj.selector, False, steps), call(self.obj.selector, False, steps), call(self.obj.selector, True, steps), call(self.obj.selector, True, 20)])
        
        self.jsonrpc.scrollBackward.return_value = True
        self.assertTrue(self.obj.scroll.horiz.backward())
        self.assertTrue(self.obj.scroll.horizentally.backward())
        self.assertTrue(self.obj.scroll.vert.backward())
        self.assertTrue(self.obj.scroll.vertically.backward(steps=20))
        self.assertEqual(self.jsonrpc.scrollBackward.call_args_list,
                         [call(self.obj.selector, False, steps), call(self.obj.selector, False, steps), call(self.obj.selector, True, steps), call(self.obj.selector, True, 20)])
        
        self.jsonrpc.scrollToBeginning.return_value = True
        self.assertTrue(self.obj.scroll.horiz.toBeginning())
        self.assertTrue(self.obj.scroll.horizentally.toBeginning())
        self.assertTrue(self.obj.scroll.vert.toBeginning())
        self.assertTrue(self.obj.scroll.vertically.toBeginning(steps=20, max_swipes=100))
        self.assertEqual(self.jsonrpc.scrollToBeginning.call_args_list,
                         [call(self.obj.selector, False, max_swipes, steps), call(self.obj.selector, False, max_swipes, steps), call(self.obj.selector, True, max_swipes, steps), call(self.obj.selector, True, 100, 20)])
        self.jsonrpc.scrollToEnd.return_value = True
        self.assertTrue(self.obj.scroll.horiz.toEnd())
        self.assertTrue(self.obj.scroll.horizentally.toEnd())
        self.assertTrue(self.obj.scroll.vert.toEnd())
        self.assertTrue(self.obj.scroll.vertically.toEnd(steps=20, max_swipes=100))
        self.assertEqual(self.jsonrpc.scrollToEnd.call_args_list,
                         [call(self.obj.selector, False, max_swipes, steps), call(self.obj.selector, False, max_swipes, steps), call(self.obj.selector, True, max_swipes, steps), call(self.obj.selector, True, 100, 20)])

    def test_wait(self):
        timeout = 3000
        self.jsonrpc.waitUntilGone.return_value = True
        self.assertTrue(self.obj.wait.gone())
        self.jsonrpc.waitUntilGone.assert_called_once_with(self.obj.selector, timeout)
        self.jsonrpc.waitForExists.return_value = True
        self.assertTrue(self.obj.wait.exists(timeout=10))
        self.jsonrpc.waitForExists.assert_called_once_with(self.obj.selector, 10)
