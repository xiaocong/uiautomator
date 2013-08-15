#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
"""

import jsonrpclib
import os
import urllib2
import subprocess
import time
import itertools

__version__ = "0,1"
__author__ = "Xiaocong He"


class _SelectorBuilder(object):

    """The class is to build parameters for UiSelector passed to Android device.
    """
    __fields = {
        "text": (0x01L, None),  # MASK_TEXT,
        "textContains": (0x02L, None),  # MASK_TEXTCONTAINS,
        "textMatches": (0x04L, None),  # MASK_TEXTMATCHES,
        "textStartsWith": (0x08L, None),  # MASK_TEXTSTARTSWITH,
        "className": (0x10L, None),  # MASK_CLASSNAME
        "classNameMatches": (0x20L, None),  # MASK_CLASSNAMEMATCHES
        "description": (0x40L, None),  # MASK_DESCRIPTION
        "descriptionContains": (0x80L, None),  # MASK_DESCRIPTIONCONTAINS
        "descriptionMatches": (0x0100L, None),  # MASK_DESCRIPTIONMATCHES
        "descriptionStartsWith": (0x0200L, None),  # MASK_DESCRIPTIONSTARTSWITH
        "checkable": (0x0400L, False),  # MASK_CHECKABLE
        "checked": (0x0800L, False),  # MASK_CHECKED
        "clickable": (0x1000L, False),  # MASK_CLICKABLE
        "longClickable": (0x2000L, False),  # MASK_LONGCLICKABLE,
        "scrollable": (0x4000L, False),  # MASK_SCROLLABLE,
        "enabled": (0x8000L, False),  # MASK_ENABLED,
        "focusable": (0x010000L, False),  # MASK_FOCUSABLE,
        "focused": (0x020000L, False),  # MASK_FOCUSED,
        "selected": (0x040000L, False),  # MASK_SELECTED,
        "packageName": (0x080000L, None),  # MASK_PACKAGENAME,
        "packageNameMatches": (0x100000L, None),  # MASK_PACKAGENAMEMATCHES,
        "resourceId": (0x200000L, None),  # MASK_RESOURCEID,
        "resourceIdMatches": (0x400000L, None),  # MASK_RESOURCEIDMATCHES,
        "index": (0x800000L, 0),  # MASK_INDEX,
        "instance": (0x01000000L, 0),  # MASK_INSTANCE,
        "fromParent": (0x02000000L, None),  # MASK_FROMPARENT,
        "childSelector": (0x04000000L, None)  # MASK_CHILDSELECTOR
    }
    __mask = "mask"

    def __init__(self, **kwargs):
        self._dict = {k: v[1] for k, v in self.__fields.items()}
        self._dict[self.__mask] = 0

        for k, v in kwargs.items():
            if k in self.__fields:
                self[k] = v

    def __getitem__(self, k):
        return self._dict[k]

    def __setitem__(self, k, v):
        if k in self.__fields:
            self._dict[k] = v  # call the method in superclass
            self._dict[self.__mask] = self[self.__mask] | self.__fields[k][0]
        else:
            raise ReferenceError("%s is not allowed." % k)

    def __delitem__(self, k):
        if k in self.__fields:
            self[k] = self.__fields[k][1]
            self[self.__mask] = self[self.__mask] & ~self.__fields[k][0]

    def build(self):
        d = self._dict.copy()
        for k, v in d.items():
            # if isinstance(v, SelectorBuilder):
            # TODO workaround.
            # something wrong in the module loader, likely SelectorBuilder was
            # loaded as another type...
            if k in ["childSelector", "fromParent"] and v is not None:
                d[k] = v.build()
        return d

    def keys(self):
        return self.__fields.keys()

SelectorBuilder = _SelectorBuilder


def rect(top=0, left=0, bottom=100, right=100):
    return {"top": top, "left": left, "bottom": bottom, "right": right}


def point(x=0, y=0):
    return {"x": x, "y": y}


_adb_cmd = None


def get_adb():
    global _adb_cmd
    if _adb_cmd is None:
        if "ANDROID_HOME" in os.environ:
            _adb_cmd = os.environ["ANDROID_HOME"] + "/platform-tools/adb"
            if not os.path.exists(_adb_cmd):
                raise EnvironmentError(
                    "Adb not found in $ANDROID_HOME path: %s." % os.environ["ANDROID_HOME"])
        else:
            import distutils
            _adb_cmd = distutils.spawn.find_executable("adb")
            if _adb_cmd is not None:
                _adb_cmd = os.path.realpath(cmd)
            else:
                raise EnvironmentError("$ANDROID_HOME environment not set.")
    return _adb_cmd


def adb_cmd(*args):
    return subprocess.Popen(["%s %s" % (get_adb(), " ".join(args))], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def adb_devices():
    '''check if device is attached.'''
    out = adb_cmd("devices").communicate()[0]
    match = "List of devices attached"
    index = out.find(match)
    if index < 0:
        raise EnvironmentError("adb is not working.")
    return dict([s.split() for s in out[index + len(match):].strip().splitlines()])


class _AutomatorServer(object):

    """start and quit rpc server on device.
    """
    __jar_files = {
        "bundle.jar": 'https://github.com/xiaocong/android-uiautomator-jsonrpcserver/blob/release/dist/bundle.jar?raw=true',
        "uiautomator-stub.jar": "https://github.com/xiaocong/android-uiautomator-jsonrpcserver/blob/release/dist/uiautomator-stub.jar?raw=true"
    }

    def __init__(self):
        self.__automator_process = None
        self.__jar_pushed = False
        self.__local_port = 9008
        self.__device_port = 9008

    def __get__(self, instance, owner):
        return self

    def __download_and_push(self):
        if not self.__jar_pushed:
            lib_path = "./libs/"
            if not os.path.exists(lib_path):
                os.mkdir(lib_path)
            for jar in self.__jar_files:
                jarfile = lib_path + jar
                if not os.path.exists(jarfile):  # not exist, then download it
                    u = urllib2.urlopen(self.__jar_files[jar])
                    with open(jarfile, 'w') as f:
                        f.write(u.read())
                # push to device
                adb_cmd("push", jarfile, "/data/local/tmp/").wait()
        self.__jar_pushed = True
        return self.__jar_files.keys()

    def __adb_forward(self, local_port, device_port):
        adb_cmd("forward", "tcp:%d" %
                local_port, "tcp:%d" % device_port).wait()

    @property
    def jsonrpc(self):
        if not self.alive:  # start server if not
            self.start()
        return jsonrpclib.Server(self.rpc_uri)

    def start(self, local_port=9008, device_port=9008): #TODO add customized local remote port.
        self.__local_port = local_port
        self.__device_port = device_port
        devices = adb_devices()
        if len(devices) is 0:
            raise EnvironmentError("Device not attached.")
        elif len(devices) > 1 and "ANDROID_SERIAL" not in os.environ:
            raise EnvironmentError(
                "Multiple devices attaches but $ANDROID_SERIAL environment not set.")

        files = self.__download_and_push()
        cmd = ["shell", "uiautomator", "runtest"] + \
            files + ["-c", "com.github.uiautomatorstub.Stub"]
        self.__automator_process = adb_cmd(*cmd)
        self.__adb_forward(local_port, 9008)
                          # TODO device_port, currently only 9008
        while not self.__can_ping():
            time.sleep(0.1)

    def __can_ping(self):
        try:
            return jsonrpclib.Server(self.rpc_uri).ping() == "pong" # not use self.jsonrpc here to avoid recursive invoke
        except:
            return False

    @property
    def alive(self):
        return self.__can_ping()

    def stop(self):
        if self.__automator_process is not None and self.__automator_process.poll() is None:
            try:
                urllib2.urlopen(self.stop_uri)
                self.__automator_process.wait()
            except:
                self.__automator_process.kill()
            finally:
                self.__automator_process = None
        out = adb_cmd("shell", "ps", "-C", "uiautomator").communicate()[
            0].strip().splitlines()
        index = out[0].split().index("PID")
        for line in out[1:]:
            adb_cmd("shell", "kill", "-9", line.split()[index]).wait()

    @property
    def stop_uri(self):
        return "http://localhost:%d/stop" % self.__local_port

    @property
    def rpc_uri(self):
        return "http://localhost:%d/jsonrpc/device" % self.__local_port


class _AutomatorDevice(object):

    '''uiautomator wrapper of android device'''
    server = _AutomatorServer()

    _orientation = (  # device orientation
        (0, "natural", "n", 0),
        (1, "left", "l", 90),
        (2, "upsidedown", "u", 180),
        (3, "right", "r", 270)
    )

    def __init__(self):
        pass

    def __call__(self, **kwargs):
        return _AutomatorDeviceObject(self.server.jsonrpc, **kwargs)

    def ping(self):
        '''ping the device, by default it returns "pong".'''
        return self.server.jsonrpc.ping()

    @property
    def info(self):
        '''Get the device info.'''
        return self.server.jsonrpc.deviceInfo()

    def click(self, x, y):
        '''click at arbitrary coordinates.'''
        self.server.jsonrpc.click(x, y)

    def swipe(self, sx, sy, ex, ey, steps=100):
        return self.server.jsonrpc.swipe(sx, sy, ex, ey, steps)

    def drag(self, sx, sy, ex, ey, steps=100):
        '''Swipe from one point to another point.'''
        return self.server.jsonrpc.drag(sx, sy, ex, ey, steps)

    def dump(self, filename):
        '''dump device window and pull to local file.'''
        device_file = self.server.jsonrpc.dumpWindowHierarchy(True, "dump.xml")
        if device_file is None or len(device_file) is 0:
            return None
        p = adb_cmd("pull", device_file, filename)
        p.wait()
        adb_cmd("shell", "rm", device_file)
        return filename if p.returncode is 0 else None

    def screenshot(self, filename, scale=1.0, quality=100):
        '''take screenshot.'''
        device_file = self.server.jsonrpc.takeScreenshot(
            "screenshot.png", scale, quality)
        if device_file is None or len(device_file) is 0:
            return None
        p = adb_cmd("pull", device_file, filename)
        p.wait()
        adb_cmd("shell", "rm", device_file)
        return filename if p.returncode is 0 else None

    def freeze_rotation(self, freeze=True):
        '''freeze or unfreeze the device rotation in current status.'''
        self.server.jsonrpc.freezeRotation(freeze)

    @property
    def orientation(self):
        '''
        orienting the devie to left/right or natural.
        left/l:       rotation=90 , displayRotation=1
        right/r:      rotation=270, displayRotation=3
        natural/n:    rotation=0  , displayRotation=0
        upsidedown/u: rotation=180, displayRotation=2
        '''
        return self._orientation[self.info["displayRotation"]][1]

    @orientation.setter
    def orientation(self, value):
        '''setter of orientation property.'''
        for values in self._orientation:
            if value in values:
                # can not set upside-down until api level 18.
                self.server.jsonrpc.setOrientation(values[1])
                break
        else:
            raise ValueError("Invalid orientation.")

    @property
    def last_traversed_text(self):
        '''get last traversed text. used in webview for highlighted text.'''
        return self.server.jsonrpc.getLastTraversedText()

    def clear_traversed_text(self):
        '''clear the last traversed text.'''
        self.server.jsonrpc.clearLastTraversedText()

    def notification(self):
        '''open notification.'''
        return self.server.jsonrpc.openNotification()

    def quick_settings(self):
        '''open quick settings.'''
        return self.server.jsonrpc.openQuickSettings()

    def watcher_triggered(self, name):
        '''check if the registered watcher was triggered.'''
        return self.server.jsonrpc.hasWatcherTriggered(name)

    def press(self, key, meta=None):
        '''
        press key via name or key code. Supported key name includes:
        home, back, left, right, up, down, center, menu, search, enter,
        delete(or del), recent(recent apps), voulmn_up, volumn_down,
        volumn_mute, camera, power
        '''
        if isinstance(key, int):
            return self.server.jsonrpc.pressKeyCode(key, meta) if meta else self.server.jsonrpc.pressKeyCode(key)
        else:
            return self.server.jsonrpc.pressKey(str(key))

    def wakeup(self):
        '''turn on screen in case of screen off.'''
        self.server.jsonrpc.wakeUp()

    def sleep(self):
        '''turn off screen in case of screen on.'''
        self.server.jsonrpc.sleep()

    def screenon():
        doc = "screen on or off."

        def fget(self):
            return self.server.jsonrpc.isScreenOn()

        def fset(self, value):
            if value:
                self.wakeup()
            else:
                self.sleep()
        return locals()
    screenon = property(**screenon())

    def wait_for_idle(self, timeout=1000):
        '''Waits for the current application to idle.'''
        self.server.jsonrpc.waitForIdle(timeout)

    def wait_for_window_update(self, package_name=None, timeout=1000):
        '''
        Waits for a window content update event to occur. If a package name
        for the window is specified, but the current window does not have the
        same package name, the function returns immediately.
        '''
        return self.server.jsonrpc.waitForWindowUpdate(package_name, timeout)


class _AutomatorDeviceObject(object):

    '''Represent a UiObject, on which user can perform actions, such as click, set text
    '''
    __action_properties = (
        ["scroll", "fling", "drag"],
        ["vert", "vertically", "horiz", "horizentally"],
        ["to", "toBeginning", "toEnd", "forward", "backward"]
    )

    def __init__(self, jsonrpc, **kwargs):
        self.jsonrpc = jsonrpc
        self.__selector = SelectorBuilder(**kwargs)
        self.__actions = []

    @property
    def selector(self):
        return self.__selector.build()

    def child_selector(self, **kwargs):
        '''set chileSelector.'''
        self.__selector["childSelector"] = SelectorBuilder(**kwargs)
        return self

    def from_parent(self, **kwargs):
        '''set fromParent selector.'''
        self.__selector["fromParent"] = SelectorBuilder(**kwargs)
        return self

    def exist(self):
        '''check if the object exists in current window.'''
        return self.jsonrpc.exist(self.selector)

    def __getattribute__(self, attr):
        '''alias of fields in info property.'''
        try:
            return super(_AutomatorDeviceObject, self).__getattribute__(attr)
        except AttributeError:
            if any(attr in l for l in self.__action_properties):
                self.__actions.append(attr)
                return self
            info = self.info
            alias = {'description': "contentDescription"}
            if attr in info:
                return info[attr]
            elif attr in alias:
                return info[alias[attr]]
            else:
                raise

    def __call__(self, *args, **kwargs):
        actions, self.__actions = self.__actions, []
        ad = {i: None for i in range(len(self.__action_properties))}
        for a in actions:
            for k, v in enumerate(self.__action_properties):
                if a in v and ad[k] is None:
                    ad[k] = a
                    break
            else:
                raise AttributeError("Invalid attributes %s." % a)
        if ad[1] in self.__action_properties[1][:2]:
            kwargs["vertical"] = True
        else:
            kwargs["vertical"] = False
        if ad[0] is "scroll":
            if ad[2] is "to":
                return self.__scroll_to(**kwargs)
            elif ad[2] is "toBeginning":
                return self.__scroll_to_beginning(**kwargs)
            elif ad[2] is "toEnd":
                return self.__scroll_to_end(**kwargs)
            elif ad[2] is "forward":
                return self.__scroll(forward=True, **kwargs)
            elif ad[2] is "backward":
                return self.__scroll(forward=False, **kwargs)
            else:
                return self.__scroll(**kwargs)
        elif ad[0] is "fling":
            if ad[2] is "toBeginning":
                return self.__fling_to_beginning(**kwargs)
            elif ad[2] is "toEnd":
                return self.__fling_to_end(**kwargs)
            elif ad[2] is "forward":
                return self.__fling(forward=True, **kwargs)
            elif ad[2] is "backward":
                return self.__scroll(forward=False, **kwargs)
            else:
                return self.__scroll(**kwargs)
        elif ad[0] is "drag" and ad[2] is "to":
            return self.__drag_to(*args, **kwargs)

        raise SyntaxError("Invalid syntax.")

    @property
    def info(self):
        '''ui object info.'''
        return self.jsonrpc.objInfo(self.selector)

    @property
    def text(self):
        '''get the text field.'''
        return self.jsonrpc.getText(self.selector)

    def set_text(self, text):
        '''set the text field.'''
        if text in [None, ""]:
            self.jsonrpc.clearTextField(self.selector)  # TODO no return
        else:
            return self.jsonrpc.setText(self.selector, text)

    def clear_text(self):
        '''clear text. alias for set_text(None).'''
        self.set_text(None)

    def click(self, corner=None):
        '''
        Perform a click action on the object. corner can be:
        tl/topleft: click on topleft corner.
        br/bottomright: click on bottomright corner.
        center/None: click on center.
        '''
        if corner is None:
            return self.jsonrpc.click(self.selector)
        elif isinstance(corner, str) and corner.lower() in ["tl", "topleft", "br", "bottomright", "center"]:
            return self.jsonrpc.click(self.selector, corner)
        raise SyntaxError("Invalid parameters.")

    def click_and_wait_for_new_window(self, timeout=1000):
        '''
        Performs a click at the center of the visible bounds of the UI element
        represented by this UiObject and waits for window transitions.
        '''
        return self.jsonrpc.clickAndWaitForNewWindow(self.selector, timeout)

    def long_click(self, corner=None):
        '''
        Perform a long click action on the object. corner can be:
        tl/topleft: click on topleft corner.
        br/bottomright: click on bottomright corner.
        center/None: click on center.
        '''
        if corner is None:
            return self.jsonrpc.longClick(self.selector)
        elif isinstance(corner, str) and corner.lower() in ["tl", "topleft", "br", "bottomright", "center"]:
            return self.jsonrpc.longClick(self.selector, corner)
        raise SyntaxError("Invalid parameters.")

    def __drag_to_coordinates(self, x, y, steps=100):
        return self.jsonrpc.dragTo(self.selector, x, y, steps)

    def __drag_to_obj(self, steps=100, **kwargs):
        return self.jsonrpc.dragTo(self.selector, SelectorBuilder(**kwargs).build(), steps)

    def __drag_to(self, *args, **kwargs):
        if len(args) >= 2 or "x" in kwargs or "y" in kwargs:
            return self.__drag_to_coordinates(*args, **kwargs)
        else:
            return self.__drag_to_obj(*args, **kwargs)

    def __fling(self, vertical=True, forward=True):
        '''fling forward/backward.'''
        return self.jsonrpc.flingForward(self.selector, vertical) if forward else self.jsonrpc.flingBackward(self.selector, vertical)

    def __fling_to_beginning(self, vertical=True, max_swipes=1000):
        '''fling to beginning.'''
        return self.jsonrpc.flingToBeginning(self.selector, vertical, max_swipes)

    def __fling_to_end(self, vertical=True, max_swipes=1000):
        '''fling to end.'''
        return self.jsonrpc.flingToEnd(self.selector, vertical, max_swipes)

    def __scroll(self, vertical=True, steps=50, forward=True):
        '''scroll forward/backward.'''
        return self.jsonrpc.scrollForward(self.selector, vertical, steps) if forward else self.jsonrpc.scrollBackward(self.selector, vertical, steps)

    def __scroll_to_beginning(self, vertical=True, steps=50, max_swipes=1000):
        '''scroll to beginning.'''
        return self.jsonrpc.scrollToBeginning(self.selector, vertical, max_swipes, steps)

    def __scroll_to_end(self, vertical=True, steps=50, max_swipes=1000):
        '''scroll to end.'''
        return self.jsonrpc.scrollToEnd(self.selector, vertical, max_swipes, steps)

    def __scroll_to(self, vertical=True, **kwargs):
        '''scroll until a ui object visible.'''
        return self.jsonrpc.scrollTo(self.selector, SelectorBuilder(**kwargs).build(), vertical)


device = _AutomatorDevice()
