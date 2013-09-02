#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
"""

import os
import subprocess
import time
import itertools
import tempfile
import json
import hashlib

try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

__version__ = "0.1.10"
__author__ = "Xiaocong He"
__all__ = ["device", "rect", "point", "adb", "Selector"]


def param_to_property(*props, **kwprops):
    if props and kwprops:
        raise SyntaxError("Can not set both props and kwprops at the same time.")

    class Wrapper(object):

        def __init__(self, func):
            self.func = func
            self.kwargs, self.args = {}, []

        def __getattr__(self, attr):
            if kwprops:
                for prop_name, prop_values in kwprops.items():
                    if attr in prop_values and prop_name not in self.kwargs:
                        self.kwargs[prop_name] = attr
                        return self
            elif attr in props:
                self.args.append(attr)
                return self
            raise AttributeError("%s parameter is duplicated or not allowed!" % attr)

        def __call__(self, *args, **kwargs):
            if kwprops:
                kwargs.update(self.kwargs)
                self.kwargs = {}
                return self.func(*args, **kwargs)
            else:
                new_args, self.args = self.args + list(args), []
                return self.func(*new_args, **kwargs)
    return Wrapper


class JsonRPCMethod(object):

    def __init__(self, url, method, timeout=30):
        self.url, self.method, self.timeout = url, method, timeout

    def __call__(self, *args, **kwargs):
        if args and kwargs:
            raise SyntaxError("Could not accept both *args and **kwargs as JSONRPC parameters.")
        data = {"jsonrpc": "2.0", "method": self.method, "id": self.id()}
        if args:
            data["params"] = args
        elif kwargs:
            data["params"] = kwargs
        req = urllib2.Request(self.url,
                              json.dumps(data).encode("utf-8"),
                              {"Content-type": "application/json"})
        result = urllib2.urlopen(req, timeout=self.timeout)
        if result is None or result.getcode() != 200:
            raise Exception("Error reponse from jsonrpc server.")
        jsonresult = json.loads(result.read().decode("utf-8"))
        if "error" in jsonresult and jsonresult["error"]:
            raise Exception("Error response. Error code: %d, Error message: %s" %
                            (jsonresult["error"]["code"], jsonresult["error"]["message"]))
        return jsonresult["result"]

    def id(self):
        m = hashlib.md5()
        m.update(("%s at %f" % (self.method, time.time())).encode("utf-8"))
        return m.hexdigest()


class JsonRPCClient(object):

    def __init__(self, url, timeout=30):
        self.url = url
        self.timeout = timeout

    def __getattr__(self, method):
        return JsonRPCMethod(self.url, method, timeout=self.timeout)


class Selector(dict):

    """The class is to build parameters for UiSelector passed to Android device.
    """
    __fields = {
        "text": (0x01, None),  # MASK_TEXT,
        "textContains": (0x02, None),  # MASK_TEXTCONTAINS,
        "textMatches": (0x04, None),  # MASK_TEXTMATCHES,
        "textStartsWith": (0x08, None),  # MASK_TEXTSTARTSWITH,
        "className": (0x10, None),  # MASK_CLASSNAME
        "classNameMatches": (0x20, None),  # MASK_CLASSNAMEMATCHES
        "description": (0x40, None),  # MASK_DESCRIPTION
        "descriptionContains": (0x80, None),  # MASK_DESCRIPTIONCONTAINS
        "descriptionMatches": (0x0100, None),  # MASK_DESCRIPTIONMATCHES
        "descriptionStartsWith": (0x0200, None),  # MASK_DESCRIPTIONSTARTSWITH
        "checkable": (0x0400, False),  # MASK_CHECKABLE
        "checked": (0x0800, False),  # MASK_CHECKED
        "clickable": (0x1000, False),  # MASK_CLICKABLE
        "longClickable": (0x2000, False),  # MASK_LONGCLICKABLE,
        "scrollable": (0x4000, False),  # MASK_SCROLLABLE,
        "enabled": (0x8000, False),  # MASK_ENABLED,
        "focusable": (0x010000, False),  # MASK_FOCUSABLE,
        "focused": (0x020000, False),  # MASK_FOCUSED,
        "selected": (0x040000, False),  # MASK_SELECTED,
        "packageName": (0x080000, None),  # MASK_PACKAGENAME,
        "packageNameMatches": (0x100000, None),  # MASK_PACKAGENAMEMATCHES,
        "resourceId": (0x200000, None),  # MASK_RESOURCEID,
        "resourceIdMatches": (0x400000, None),  # MASK_RESOURCEIDMATCHES,
        "index": (0x800000, 0),  # MASK_INDEX,
        "instance": (0x01000000, 0),  # MASK_INSTANCE,
        "fromParent": (0x02000000, None),  # MASK_FROMPARENT,
        "childSelector": (0x04000000, None)  # MASK_CHILDSELECTOR
    }
    __mask = "mask"

    def __init__(self, **kwargs):
        super(Selector, self).__setitem__(self.__mask, 0)
        for k in kwargs:
            self[k] = kwargs[k]

    def __setitem__(self, k, v):
        if k in self.__fields:
            super(Selector, self).__setitem__(k, v)
            super(Selector, self).__setitem__(self.__mask, self[self.__mask] | self.__fields[k][0])
        else:
            raise ReferenceError("%s is not allowed." % k)

    def __delitem__(self, k):
        if k in self.__fields:
            super(Selector, self).__delitem__(k)
            super(Selector, self).__setitem__(self.__mask, self[self.__mask] & ~self.__fields[k][0])


def rect(top=0, left=0, bottom=100, right=100):
    return {"top": top, "left": left, "bottom": bottom, "right": right}


def point(x=0, y=0):
    return {"x": x, "y": y}


class Adb(object):

    def __init__(self):
        self.__adb_cmd = None

    @property
    def adb(self):
        if self.__adb_cmd is None:
            if "ANDROID_HOME" in os.environ:
                filename = "adb.exe" if os.name == 'nt' else "adb"
                adb_cmd = os.path.join(os.environ["ANDROID_HOME"], "platform-tools", filename)
                if not os.path.exists(adb_cmd):
                    raise EnvironmentError(
                        "Adb not found in $ANDROID_HOME path: %s." % os.environ["ANDROID_HOME"])
            else:
                import distutils
                adb_cmd = distutils.spawn.find_executable("adb")
                if adb_cmd:
                    adb_cmd = os.path.realpath(adb_cmd)
                else:
                    raise EnvironmentError("$ANDROID_HOME environment not set.")
            self.__adb_cmd = adb_cmd
        return self.__adb_cmd

    def cmd(self, *args):
        '''adb command. return the subprocess.Popen object.'''
        return subprocess.Popen(["%s %s" % (self.adb, " ".join(args))], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    @property
    def devices(self):
        '''get a dict of attached devices. key is the device serial, value is device name.'''
        out = self.cmd("devices").communicate()[0].decode("utf-8")
        match = "List of devices attached"
        index = out.find(match)
        if index < 0:
            raise EnvironmentError("adb is not working.")
        return dict([s.split() for s in out[index + len(match):].strip().splitlines() if s.strip()])

    def forward(self, local_port, device_port):
        '''adb port forward. return 0 if success, else non-zero.'''
        return self.cmd("forward", "tcp:%d" % local_port, "tcp:%d" % device_port).wait()

    @property
    def forward_list(self):
        lines = self.cmd("forward", "--list").communicate()[0].decode("utf-8").strip().splitlines()
        forwards = [line.strip().split() for line in lines if line.strip()]
        return dict([(d[0], [int(d[1][4:]), int(d[2][4:])]) for d in forwards if d[2] == "tcp:%d" % server_port() and d[1].startswith("tcp:")])

adb = Adb()


def server_port():
    return int(os.environ["JSONRPC_PORT"]) if "JSONRPC_PORT" in os.environ else 9008


class AutomatorServer(object):

    """start and quit rpc server on device.
    """
    __jar_files = {
        "bundle.jar": 'https://github.com/xiaocong/android-uiautomator-jsonrpcserver/blob/release/dist/bundle.jar?raw=true',
        "uiautomator-stub.jar": "https://github.com/xiaocong/android-uiautomator-jsonrpcserver/blob/release/dist/uiautomator-stub.jar?raw=true"
    }

    def __init__(self):
        self.__local_port = None
        self.uiautomator_process = None
        self.__jsonrpc_client = None

    def download_and_push(self):
        lib_path = os.path.join(tempfile.gettempdir(), "libs")
        if not os.path.exists(lib_path):
            os.mkdir(lib_path)
        for jar in self.__jar_files:
            jarfile = os.path.join(lib_path, jar)
            if not os.path.exists(jarfile):  # not exist, then download it
                u = urllib2.urlopen(self.__jar_files[jar])
                with open(jarfile, 'wb') as f:
                    f.write(u.read())
            # push to device
            adb.cmd("push", jarfile, "/data/local/tmp/").wait()
        return list(self.__jar_files.keys())

    @property
    def jsonrpc(self):
        if not self.alive:  # start server if not
            self.start()
        return self.__jsonrpc()

    def __jsonrpc(self):
        if not self.__jsonrpc_client and self.local_port:
            self.__jsonrpc_client = JsonRPCClient(self.rpc_uri)
        return self.__jsonrpc_client

    def device_serial(self):
        devices = adb.devices
        if not devices:
            raise EnvironmentError("Device not attached.")
        elif len(devices) > 1 and ("ANDROID_SERIAL" not in os.environ or os.environ["ANDROID_SERIAL"] not in devices):
            raise EnvironmentError("Multiple devices attaches but $ANDROID_SERIAL environment incorrect.")
        if "ANDROID_SERIAL" not in os.environ:
            os.environ["ANDROID_SERIAL"] = list(devices.keys())[0]
        return os.environ["ANDROID_SERIAL"]

    @property
    def local_port(self):
        if not self.__local_port:
            self.__local_port = adb.forward_list.get(self.device_serial(), [None])[0]

        return self.__local_port

    def start(self):
        files = self.download_and_push()
        cmd = list(itertools.chain(["shell", "uiautomator", "runtest"],
                                   files,
                                   ["-c", "com.github.uiautomatorstub.Stub"]))
        self.uiautomator_process = adb.cmd(*cmd)
        if not self.local_port:
            ports = [v[0] for v in adb.forward_list.values()]
            if not any(adb.forward(port, server_port()) == 0 for port in range(9008, 9200) if port not in ports):
                raise IOError("Error during start jsonrpc server!")

        timeout = 5
        while not self.alive and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1
        if not self.alive:
            raise IOError("RPC server not started!")

    def ping(self):
        try:
            return self.__jsonrpc().ping() if self.__jsonrpc() else None
        except:
            return None

    @property
    def alive(self):
        '''Check if the rpc server is alive.'''
        return self.ping() == "pong"

    def stop(self):
        '''Stop the rpc server.'''
        if self.uiautomator_process and self.uiautomator_process.poll() is None:
            try:
                urllib2.urlopen(self.stop_uri)
                self.uiautomator_process.wait()
            except:
                self.uiautomator_process.kill()
            finally:
                self.uiautomator_process = None
        out = adb.cmd("shell", "ps", "-C", "uiautomator").communicate()[0].decode("utf-8").strip().splitlines()
        if out:
            index = out[0].split().index("PID")
            for line in out[1:]:
                if len(line.split()) > index:
                    adb.cmd("shell", "kill", "-9", line.split()[index]).wait()

    @property
    def stop_uri(self):
        return "http://localhost:%d/stop" % self.local_port

    @property
    def rpc_uri(self):
        return "http://localhost:%d/jsonrpc/0" % self.local_port


class AutomatorDevice(object):

    '''uiautomator wrapper of android device'''
    server = AutomatorServer()

    __orientation = (  # device orientation
        (0, "natural", "n", 0),
        (1, "left", "l", 90),
        (2, "upsidedown", "u", 180),
        (3, "right", "r", 270)
    )
    __alias = {
        "width": "displayWidth",
        "height": "displayHeight"
    }

    def __call__(self, **kwargs):
        return AutomatorDeviceObject(self, **kwargs)

    def __getattr__(self, attr):
        '''alias of fields in info property.'''
        info = self.info
        if attr in info:
            return info[attr]
        elif attr in self.__alias:
            return info[self.__alias[attr]]
        else:
            raise AttributeError("%s attribute not found!" % attr)

    @property
    def info(self):
        '''Get the device info.'''
        return self.server.jsonrpc.deviceInfo()

    def click(self, x, y):
        '''click at arbitrary coordinates.'''
        return self.server.jsonrpc.click(x, y)

    def swipe(self, sx, sy, ex, ey, steps=100):
        return self.server.jsonrpc.swipe(sx, sy, ex, ey, steps)

    def drag(self, sx, sy, ex, ey, steps=100):
        '''Swipe from one point to another point.'''
        return self.server.jsonrpc.drag(sx, sy, ex, ey, steps)

    def dump(self, filename):
        '''dump device window and pull to local file.'''
        device_file = self.server.jsonrpc.dumpWindowHierarchy(True, "dump.xml")
        if not device_file:
            return None
        p = adb.cmd("pull", device_file, filename)
        p.wait()
        adb.cmd("shell", "rm", device_file).wait()
        return filename if p.returncode is 0 else None

    def screenshot(self, filename, scale=1.0, quality=100):
        '''take screenshot.'''
        device_file = self.server.jsonrpc.takeScreenshot("screenshot.png",
                                                         scale, quality)
        if not device_file:
            return None
        p = adb.cmd("pull", device_file, filename)
        p.wait()
        adb.cmd("shell", "rm", device_file).wait()
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
        return self.__orientation[self.info["displayRotation"]][1]

    @orientation.setter
    def orientation(self, value):
        '''setter of orientation property.'''
        for values in self.__orientation:
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

    @property
    def open(self):
        '''
        Open notification or quick settings.
        Usage:
        d.open.notification()
        d.open.quick_settings()
        '''
        @param_to_property(action=["notification", "quick_settings"])
        def _open(action):
            if action == "notification":
                return self.server.jsonrpc.openNotification()
            else:
                return self.server.jsonrpc.openQuickSettings()
        return _open

    @property
    def watchers(self):
        obj = self

        class Watchers(list):

            def __init__(self):
                for watcher in obj.server.jsonrpc.getWatchers():
                    self.append(watcher)

            @property
            def triggered(self):
                return obj.server.jsonrpc.hasAnyWatcherTriggered()

            def remove(self, name=None):
                if name:
                    obj.server.jsonrpc.removeWatcher(name)
                else:
                    for name in self:
                        obj.server.jsonrpc.removeWatcher(name)

            def reset(self):
                obj.server.jsonrpc.resetWatcherTriggers()
                return self

            def run(self):
                obj.server.jsonrpc.runWatchers()
                return self
        return Watchers()

    def watcher(self, name):
        obj = self

        class Watcher(object):

            def __init__(self):
                self.__selectors = []

            @property
            def triggered(self):
                return obj.server.jsonrpc.hasWatcherTriggered(name)

            def remove(self):
                obj.server.jsonrpc.removeWatcher(name)

            def when(self, **kwargs):
                self.__selectors.append(Selector(**kwargs))
                return self

            def click(self, **kwargs):
                obj.server.jsonrpc.registerClickUiObjectWatcher(name, self.__selectors, Selector(**kwargs))

            @property
            def press(self):
                @param_to_property(
                    "home", "back", "left", "right", "up", "down", "center",
                    "search", "enter", "delete", "del", "recent", "volume_up",
                    "menu", "volume_down", "volume_mute", "camera", "power")
                def _press(*args):
                    obj.server.jsonrpc.registerPressKeyskWatcher(name, self.__selectors, args)
                return _press
        return Watcher()

    @property
    def press(self):
        '''
        press key via name or key code. Supported key name includes:
        home, back, left, right, up, down, center, menu, search, enter,
        delete(or del), recent(recent apps), volume_up, volume_down,
        volume_mute, camera, power.
        Usage:
        d.press.back()  # press back key
        d.press.menu()  # press home key
        d.press(89)     # press keycode
        '''
        @param_to_property(
            key=["home", "back", "left", "right", "up", "down", "center",
                 "menu", "search", "enter", "delete", "del", "recent",
                 "volume_up", "volume_down", "volume_mute", "camera", "power"]
        )
        def _press(key, meta=None):
            if isinstance(key, int):
                return self.server.jsonrpc.pressKeyCode(key, meta) if meta else self.server.jsonrpc.pressKeyCode(key)
            else:
                return self.server.jsonrpc.pressKey(str(key))
        return _press

    def wakeup(self):
        '''turn on screen in case of screen off.'''
        self.server.jsonrpc.wakeUp()

    def sleep(self):
        '''turn off screen in case of screen on.'''
        self.server.jsonrpc.sleep()

    @property
    def screen(self):
        '''
        Turn on/off screen.
        Usage:
        d.screen.on()
        d.screen.off()
        '''
        @param_to_property(action=["on", "off"])
        def _screen(action):
            return self.wakeup() if action == "on" else self.sleep()
        return _screen

    @property
    def wait(self):
        '''
        Waits for the current application to idle or window update event occurs.
        Usage:
        d.wait.idle(timeout=1000)
        d.wait.update(timeout=1000, package_name="com.android.settings")
        '''
        @param_to_property(action=["idle", "update"])
        def _wait(action, timeout=1000, package_name=None):
            if action == "idle":
                return self.server.jsonrpc.waitForIdle(timeout)
            elif action == "update":
                return self.server.jsonrpc.waitForWindowUpdate(package_name, timeout)
        return _wait

    def exists(self, **kwargs):
        '''Check if the specified ui object by kwargs exists.'''
        return self(**kwargs).exists


class AutomatorDeviceObject(object):

    '''Represent a UiObject, on which user can perform actions, such as click, set text
    '''

    __alias = {'description': "contentDescription"}

    def __init__(self, device, **kwargs):
        self.jsonrpc = device.server.jsonrpc
        self.selector = Selector(**kwargs)
        self.__actions = []

    def child_selector(self, **kwargs):
        '''set chileSelector.'''
        self.selector["childSelector"] = Selector(**kwargs)
        return self

    def from_parent(self, **kwargs):
        '''set fromParent selector.'''
        self.selector["fromParent"] = Selector(**kwargs)
        return self

    @property
    def exists(self):
        '''check if the object exists in current window.'''
        return self.jsonrpc.exist(self.selector)

    def __getattr__(self, attr):
        '''alias of fields in info property.'''
        info = self.info
        if attr in info:
            return info[attr]
        elif attr in self.__alias:
            return info[self.__alias[attr]]
        else:
            raise AttributeError("%s attribute not found!" % attr)

    @property
    def info(self):
        '''ui object info.'''
        return self.jsonrpc.objInfo(self.selector)

    def set_text(self, text):
        '''set the text field.'''
        if text in [None, ""]:
            return self.jsonrpc.clearTextField(self.selector)  # TODO no return
        else:
            return self.jsonrpc.setText(self.selector, text)

    def clear_text(self):
        '''clear text. alias for set_text(None).'''
        self.set_text(None)

    @property
    def click(self):
        '''
        click on the ui object.
        Usage:
        d(text="Clock").click()  # click on the center of the ui object
        d(text="OK").click.wait(timeout=3000) # click and wait for the new window update
        d(text="John").click.topleft() # click on the topleft of the ui object
        d(text="John").click.bottomright() # click on the bottomright of the ui object
        '''
        @param_to_property(action=["tl", "topleft", "br", "bottomright", "wait"])
        def _click(action=None, timeout=3000):
            if action is None:
                return self.jsonrpc.click(self.selector)
            elif action in ["tl", "topleft", "br", "bottomright"]:
                return self.jsonrpc.click(self.selector, action)
            else:
                return self.jsonrpc.clickAndWaitForNewWindow(self.selector, timeout)
        return _click

    @property
    def long_click(self):
        '''
        Perform a long click action on the object.
        Usage:
        d(text="Image").long_click()  # long click on the center of the ui object
        d(text="Image").long_click.topleft()  # long click on the topleft of the ui object
        d(text="Image").long_click.bottomright()  # long click on the topleft of the ui object
        '''
        @param_to_property(corner=["tl", "topleft", "br", "bottomright"])
        def _long_click(corner=None):
            if corner is None:
                return self.jsonrpc.longClick(self.selector)
            else:
                return self.jsonrpc.longClick(self.selector, corner)
        return _long_click

    @property
    def drag(self):
        '''
        Drag the ui object to other point or ui object.
        Usage:
        d(text="Clock").drag.to(x=100, y=100)  # drag to point (x,y)
        d(text="Clock").drag.to(text="Remove") # drag to another object
        '''
        def to(obj, *args, **kwargs):
            if len(args) >= 2 or "x" in kwargs or "y" in kwargs:
                drag_to = lambda x, y, steps=100: self.jsonrpc.dragTo(self.selector, x, y, steps)
            else:
                drag_to = lambda steps=100, **kwargs: self.jsonrpc.dragTo(self.selector, Selector(**kwargs), steps)
            return drag_to(*args, **kwargs)
        return type("Drag", (object,), {"to": to})()

    def gesture(self, start1, start2, *args, **kwargs):
        '''
        perform two point gesture.
        Usage:
        d().gesture(startPoint1, startPoint2).to(endPoint1, endPoint2, steps)
        d().gesture(startPoint1, startPoint2, endPoint1, endPoint2, steps)
        '''
        def to(obj_self, end1, end2, steps=100):
            return self.jsonrpc.gesture(self.selector, start1, start2,
                                        end1, end2, steps)
        obj = type("Gesture", (object,), {"to": to})()
        return obj if len(args) == 0 else to(None, *args, **kwargs)

    @property
    def pinch(self):
        '''
        Perform two point gesture from edge to center(in) or center to edge(out).
        Usages:
        d().pinch.In(percent=100, steps=10)
        d().pinch.Out(percent=100, steps=100)
        '''
        @param_to_property(in_or_out=["In", "Out"])
        def _pinch(in_or_out="Out", percent=100, steps=50):
            if in_or_out in ["Out", "out"]:
                return self.jsonrpc.pinchOut(self.selector, percent, steps)
            elif in_or_out in ["In", "in"]:
                return self.jsonrpc.pinchIn(self.selector, percent, steps)
        return _pinch

    @property
    def swipe(self):
        '''
        Perform swipe action.
        Usages:
        d().swipe.right()
        d().swipe.left(steps=10)
        d().swipe.up(steps=10)
        d().swipe.down()
        d().swipe("right", steps=20)
        '''
        @param_to_property(direction=["up", "down", "right", "left"])
        def _swipe(direction="left", steps=10):
            return self.jsonrpc.swipe(self.selector, direction, steps)
        return _swipe

    @property
    def fling(self):
        '''
        Perform fling action.
        Usage:
        d().fling()  # default vertically, forward
        d().fling.horiz.forward()
        d().fling.vert.backward()
        d().fling.toBeginning(max_swipes=100) # vertically
        d().fling.horiz.toEnd()
        '''
        @param_to_property(
            dimention=["vert", "vertically", "vertical", "horiz", "horizental", "horizentally"],
            action=["forward", "backward", "toBeginning", "toEnd"]
        )
        def _fling(dimention="vert", action="forward", max_swipes=1000):
            vertical = dimention in ["vert", "vertically", "vertical"]
            if action == "forward":
                return self.jsonrpc.flingForward(self.selector, vertical)
            elif action == "backward":
                return self.jsonrpc.flingBackward(self.selector, vertical)
            elif action == "toBeginning":
                return self.jsonrpc.flingToBeginning(self.selector, vertical, max_swipes)
            elif action == "toEnd":
                return self.jsonrpc.flingToEnd(self.selector, vertical, max_swipes)

        return _fling

    @property
    def scroll(self):
        '''
        Perfrom scroll action.
        Usage:
        d().scroll(steps=50) # default vertically and forward
        d().scroll.horiz.forward(steps=100)
        d().scroll.vert.backward(steps=100)
        d().scroll.horiz.toBeginning(steps=100, max_swipes=100)
        d().scroll.vert.toEnd(steps=100)
        d().scroll.horiz.to(text="Clock")
        '''
        def __scroll(vertical, forward, steps=100):
            method = self.jsonrpc.scrollForward if forward else self.jsonrpc.scrollBackward
            return method(self.selector, vertical, steps)

        def __scroll_to_beginning(vertical, steps=100, max_swipes=1000):
            return self.jsonrpc.scrollToBeginning(self.selector, vertical, max_swipes, steps)

        def __scroll_to_end(vertical, steps=100, max_swipes=1000):
            return self.jsonrpc.scrollToEnd(self.selector, vertical, max_swipes, steps)

        def __scroll_to(vertical, **kwargs):
            return self.jsonrpc.scrollTo(self.selector, Selector(**kwargs), vertical)

        @param_to_property(
            dimention=["vert", "vertically", "vertical", "horiz", "horizental", "horizentally"],
            action=["forward", "backward", "toBeginning", "toEnd", "to"])
        def _scroll(dimention="vert", action="forward", **kwargs):
            vertical = dimention in ["vert", "vertically", "vertical"]
            if action in ["forward", "backward"]:
                return __scroll(vertical, action == "forward", **kwargs)
            elif action == "toBeginning":
                return __scroll_to_beginning(vertical, **kwargs)
            elif action == "toEnd":
                return __scroll_to_end(vertical, **kwargs)
            elif action == "to":
                return __scroll_to(vertical, **kwargs)
        return _scroll

    @property
    def wait(self):
        '''
        Wait until the ui object gone or exist.
        Usage:
        d(text="Clock").wait.gone()  # wait until it's gone.
        d(text="Settings").wait.exists() # wait until it appears.
        '''
        @param_to_property(action=["exists", "gone"])
        def _wait(action, timeout=3000):
            method = self.jsonrpc.waitUntilGone if action == "gone" else self.jsonrpc.waitForExists
            return method(self.selector, timeout)
        return _wait

device = AutomatorDevice()
