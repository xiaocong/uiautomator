#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
"""

import jsonrpclib
import os
import urllib2
import subprocess
import time

__version__ = "0,1"
__author__ = "Xiaocong He"


class _SelectorBuilder(object):

    """The class is to build parameters for UiSelector passed to Android device.
    """
    _keys = {
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
    _mask = "mask"

    def __init__(self, **kwargs):
        self._dict = {k: v[1] for k, v in self._keys.items()}
        self._dict[self._mask] = 0

        for k, v in kwargs.items():
            if k in self._keys:
                self[k] = v

    def __getitem__(self, k):
        return self._dict[k]

    def __setitem__(self, k, v):
        if k in self._keys:
            self._dict[k] = v  # call the method in superclass
            self._dict[self._mask] = self[self._mask] | self._keys[k][0]
        else:
            raise ReferenceError("%s is not allowed." % k)

    def __delitem__(self, k):
        if k in self._keys:
            self[k] = self._keys[k][1]
            self[self._mask] = self[self._mask] & ~self._keys[k][0]

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

SelectorBuilder = _SelectorBuilder


_adb_cmd = None
def get_adb():
    global _adb_cmd
    if _adb_cmd is None:
        if "ANDROID_HOME" in os.environ:
            _adb_cmd = os.environ["ANDROID_HOME"] + "/platform-tools/adb"
            if not os.path.exists(_adb_cmd):
                raise EnvironmentError("Adb not found in $ANDROID_HOME path: %s." % os.environ["ANDROID_HOME"])
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


class _AutomatorServer(object):

    """start and quit rpc server on device.
    """
    _jar_files = {
        "bundle.jar": 'https://github.com/xiaocong/android-uiautomator-jsonrpcserver/blob/release/dist/bundle.jar?raw=true',
        "uiautomator-stub.jar": "https://github.com/xiaocong/android-uiautomator-jsonrpcserver/blob/release/dist/uiautomator-stub.jar?raw=true"
    }
 
    def __init__(self):
        self._automator_process = None
        self._jar_pushed = False
        self._local_port = 9008
        self._device_port = 9008

    def __get__(self, instance, owner):
        return self

    def devices(self):
        '''check if device is attached.'''
        out = adb_cmd("devices").communicate()[0]
        match = "List of devices attached"
        index = out.find(match)
        if index < 0:
            raise EnvironmentError("adb is not working.")
        return dict([s.split() for s in out[index + len(match):].strip().splitlines()])

    def _download_and_push(self):
        if not self._jar_pushed:
            lib_path = "./libs/"
            if not os.path.exists(lib_path):
                os.mkdir(lib_path)
            for jar in self._jar_files:
                jarfile = lib_path + jar
                if not os.path.exists(jarfile): # not exist, then download it
                    u = urllib2.urlopen(self._jar_files[jar])
                    with open(jarfile, 'w') as f:
                        f.write(u.read())
                # push to device
                adb_cmd("push", jarfile, "/data/local/tmp/").wait()
        self._jar_pushed = True
        return self._jar_files.keys()

    def _adb_forward(self, local_port, device_port):
        adb_cmd("forward", "tcp:%d" % local_port, "tcp:%d" % device_port).wait()

    @property
    def jsonrpc(self):
        if not self.alive:
            self.start()
        return jsonrpclib.Server(self.rpc_uri)

    def start(self, local_port=9008, device_port=9008): #TODO add customized local remote port.
        self._local_port = local_port
        self._device_port = device_port
        devices = self.devices()
        if len(devices) is 0:
            raise EnvironmentError("Device not attached.")
        elif len(devices) > 1 and "ANDROID_SERIAL" not in os.environ:
            raise EnvironmentError("Multiple devices attaches but $ANDROID_SERIAL environment not set.")

        files = self._download_and_push()
        cmd = ["shell", "uiautomator", "runtest"] + files + ["-c", "com.github.uiautomatorstub.Stub"]
        self._automator_process = adb_cmd(*cmd)
        self._adb_forward(local_port, 9008) #TODO device_port, currently only 9008
        while not self._can_ping():
            time.sleep(0.1)

    def _can_ping(self):
        try:
            return jsonrpclib.Server(self.rpc_uri).ping() == "pong" # not use self.jsonrpc here to avoid recursive invoke
        except:
            return False

    @property
    def alive(self):
        return self._can_ping()

    def stop(self):
        if self._automator_process is not None and self._automator_process.poll() is None:
            try:
                urllib2.urlopen(self.stop_uri)
                self._automator_process.wait()
            except:
                self._automator_process.kill()
            finally:
                self._automator_process = None
        out = adb_cmd("shell", "ps", "-C", "uiautomator").communicate()[0].strip().splitlines()
        index = out[0].split().index("PID")
        for line in out[1:]:
            adb_cmd("shell", "kill", "-9", line.split()[index]).wait()

    @property
    def stop_uri(self):
        return "http://localhost:%d/stop" % self._local_port

    @property
    def rpc_uri(self):
        return "http://localhost:%d/jsonrpc/device" % self._local_port


class _AutomatorDevice(object):
    '''uiautomator wrapper of android device'''
    server = _AutomatorServer()

    def __init__(self):
        pass

    def __call__(self, **kwargs):
        return _AutomatorDeviceObject(self.server.jsonrpc, **kwargs)

    def ping(self):
        '''ping the device, by default it returns "pong".'''
        return self.server.jsonrpc.ping()

    @property
    def device_info(self):
        '''Get the device info.'''
        return self.server.jsonrpc.deviceInfo()

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
        device_file = self.server.jsonrpc.takeScreenshot("screenshot.png", scale, quality)
        if device_file is None or len(device_file) is 0:
            return None
        p = adb_cmd("pull", device_file, filename)
        p.wait()
        adb_cmd("shell", "rm", device_file)
        return filename if p.returncode is 0 else None

    def click(self, x, y):
        self.server.jsonrpc.click(x, y)

    def press(self, key, meta=None):
        if isinstance(key, int):
            return self.server.jsonrpc.pressKeyCode(key, meta) if meta else self.server.jsonrpc.pressKeyCode(key)
        else:
            return self.server.jsonrpc.pressKey(str(key))

    def wakeup(self):
        self.server.jsonrpc.wakeUp()


class _AutomatorDeviceObject(object):
    '''Represent a UiObject, on which user can perform actions, such as click, set text
    '''
    def __init__(self, jsonrpc, **kwargs):
        self.jsonrpc = jsonrpc
        self.selector = SelectorBuilder(**kwargs)

    def child_selector(self, **kwargs):
        '''set chileSelector.'''
        self.selector["childSelector"] = SelectorBuilder(**kwargs)
        return self

    def from_parent(self, **kwargs):
        '''set fromParent selector.'''
        self.selector["fromParent"] = SelectorBuilder(**kwargs)
        return self

    def click(self, corner=None):
        if corner is None:
            return self.jsonrpc.click(self.selector.build())
        elif isinstance(corner, str) and corner.lower() in ["tl", "topleft", "br", "bottomright", "center"]:
            return self.jsonrpc.click(self.selector.build(), corner)
        raise SyntaxError("Invalid parameters.")

device = _AutomatorDevice()
