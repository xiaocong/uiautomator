#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Python wrapper for Android uiautomator tool."""

import sys
import os
import subprocess
import time
import itertools
import json
import hashlib
import socket,threading
import re,tempfile
import collections
import xml.dom.minidom
from functools import wraps
from imgUtil import ImageUtil
from comparison import isMatch, getMatchedCenterOffset
from chromdriver import ChromeDriver

DEVICE_PORT = int(os.environ.get('UIAUTOMATOR_DEVICE_PORT', '9008'))
LOCAL_PORT = int(os.environ.get('UIAUTOMATOR_LOCAL_PORT', '9008'))

if 'localhost' not in os.environ.get('no_proxy', ''):
    os.environ['no_proxy'] = "localhost,%s" % os.environ.get('no_proxy', '')

try:
    import urllib2
except ImportError:
    import urllib.request as urllib2
try:
    from httplib import HTTPException
except:
    from http.client import HTTPException
try:
    if os.name == 'nt':
        import urllib3
except:  # to fix python setup error on Windows.
    pass

__author__ = "Xiaocong He"
__all__ = ["device", "Device", "rect", "point", "Selector", "JsonRPCError"]

u2_version_code=5


def U(x):
    if sys.version_info.major == 2:
        return x.decode('utf-8') if type(x) is str else x
    elif sys.version_info.major == 3:
        return x


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

def stopUiautomator(url):
    port = url.split(":")[2].split("/")[0]
    serial = None
    try:
        lines = systemCmd(['adb','forward','--list']).communicate()[0].decode("utf-8").strip().splitlines()
        for s, lp, rp in [line.strip().split() for line in lines]:
            if lp == 'tcp:%s'%port and rp=='tcp:9008':
                serial = s
                break
    except:
        pass
    if serial:
        os.system("adb -s %s shell am force-stop com.github.uiautomator"%serial)
        

def systemCmd(cmd_line):
    '''exec system cmd, paramas list'''
    if os.name != "nt":
        cmd_line = [" ".join(cmd_line)]
    return subprocess.Popen(cmd_line, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class JsonRPCError(Exception):

    def __init__(self, code, message):
        self.code = int(code)
        self.message = message

    def __str__(self):
        return "JsonRPC Error code: %d, Message: %s" % (self.code, self.message)
    
class JsonRPCMethod(object):

    if os.name == 'nt':
        try:
            pool = urllib3.PoolManager()
        except:
            pass

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
        jsonresult = {"result": ""}
        # add mintor timeout
        t = threading.Timer(90, stopUiautomator, (self.url,))
        t.setDaemon(True)
        t.start()
        try:
#             print 'start post %s %s'%(self.url,str(data))
            result = None
            if os.name == "nt":
                res = self.pool.urlopen("POST",
                    self.url,
                    headers={"Content-Type": "application/json"},
                    body=json.dumps(data).encode("utf-8"),
                    timeout=self.timeout)
                content_type = res.headers['Content-Type']
                result = res.data
            else:
                res = None
                try:
                    req = urllib2.Request(self.url,
                        json.dumps(data).encode("utf-8"),
                        {"Content-type": "application/json"})
                    res = urllib2.urlopen(req, timeout=self.timeout)
                    content_type = res.info().getheader('Content-Type')
                    result = res.read()
                finally:
                    if res is not None:
                        res.close()
            if self.method == "screenshot":
                if content_type == "image/png":
                    return result
            jsonresult = json.loads(result.decode("utf-8"))
            if "error" in jsonresult and jsonresult["error"]:
                raise JsonRPCError(
                    jsonresult["error"]["code"],
                    "%s: %s" % (jsonresult["error"]["data"]["exceptionTypeName"], jsonresult["error"]["message"])
                )
        finally:
            try:
                t.cancel()
            except:
                pass
        return jsonresult["result"]

    def id(self):
        m = hashlib.md5()
        m.update(("%s at %f" % (self.method, time.time())).encode("utf-8"))
#         m.update("i am uiautomator".encode("utf-8"))
        return m.hexdigest()


class JsonRPCClient(object):

    def __init__(self, url, timeout=30, method_class=JsonRPCMethod):
        self.url = url
        self.timeout = timeout
        self.method_class = method_class

    def __getattr__(self, method):
        return self.method_class(self.url, method, timeout=self.timeout)


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
        "instance": (0x01000000, 0)  # MASK_INSTANCE,
    }
    __mask, __childOrSibling, __childOrSiblingSelector = "mask", "childOrSibling", "childOrSiblingSelector"

    def __init__(self, **kwargs):
        super(Selector, self).__setitem__(self.__mask, 0)
        super(Selector, self).__setitem__(self.__childOrSibling, [])
        super(Selector, self).__setitem__(self.__childOrSiblingSelector, [])
        for k in kwargs:
            self[k] = kwargs[k]

    def __setitem__(self, k, v):
        if k in self.__fields:
            super(Selector, self).__setitem__(U(k), U(v))
            super(Selector, self).__setitem__(self.__mask, self[self.__mask] | self.__fields[k][0])
        else:
            raise ReferenceError("%s is not allowed." % k)

    def __delitem__(self, k):
        if k in self.__fields:
            super(Selector, self).__delitem__(k)
            super(Selector, self).__setitem__(self.__mask, self[self.__mask] & ~self.__fields[k][0])

    def clone(self):
        kwargs = dict((k, self[k]) for k in self
                      if k not in [self.__mask, self.__childOrSibling, self.__childOrSiblingSelector])
        selector = Selector(**kwargs)
        for v in self[self.__childOrSibling]:
            selector[self.__childOrSibling].append(v)
        for s in self[self.__childOrSiblingSelector]:
            selector[self.__childOrSiblingSelector].append(s.clone())
        return selector

    def child(self, **kwargs):
        self[self.__childOrSibling].append("child")
        self[self.__childOrSiblingSelector].append(Selector(**kwargs))
        return self

    def sibling(self, **kwargs):
        self[self.__childOrSibling].append("sibling")
        self[self.__childOrSiblingSelector].append(Selector(**kwargs))
        return self

    child_selector, from_parent = child, sibling


def rect(top=0, left=0, bottom=100, right=100):
    return {"top": top, "left": left, "bottom": bottom, "right": right}


def intersect(rect1, rect2):
    top = rect1["top"] if rect1["top"] > rect2["top"] else rect2["top"]
    bottom = rect1["bottom"] if rect1["bottom"] < rect2["bottom"] else rect2["bottom"]
    left = rect1["left"] if rect1["left"] > rect2["left"] else rect2["left"]
    right = rect1["right"] if rect1["right"] < rect2["right"] else rect2["right"]
    return left, top, right, bottom


def point(x=0, y=0):
    return {"x": x, "y": y}


class Adb(object):

    def __init__(self, serial=None, adb_server_host=None, adb_server_port=None):
        self.__adb_cmd = None
        self.default_serial = serial if serial else os.environ.get("ANDROID_SERIAL", None)
        self.adb_server_host = str(adb_server_host if adb_server_host else 'localhost')
        self.adb_server_port = str(adb_server_port if adb_server_port else '5037')
        self.adbHostPortOptions = []
        if self.adb_server_host not in ['localhost', '127.0.0.1']:
            self.adbHostPortOptions += ["-H", self.adb_server_host]
        if self.adb_server_port != '5037':
            self.adbHostPortOptions += ["-P", self.adb_server_port]

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
                if "spawn" not in dir(distutils):
                    import distutils.spawn
                adb_cmd = distutils.spawn.find_executable("adb")
                if adb_cmd:
                    adb_cmd = os.path.realpath(adb_cmd)
                else:
                    raise EnvironmentError("$ANDROID_HOME environment not set.")
            self.__adb_cmd = adb_cmd
        return self.__adb_cmd

    def cmd(self, *args, **kwargs):
        '''adb command, add -s serial by default. return the subprocess.Popen object.'''
        serial = self.device_serial()
        if serial:
            if " " in serial:  # TODO how to include special chars on command line
                serial = "'%s'" % serial
            return self.raw_cmd(*["-s", serial] + list(args))
        else:
            return self.raw_cmd(*args)

    def raw_cmd(self, *args):
        '''adb command. return the subprocess.Popen object.'''
        cmd_line = [self.adb()] + self.adbHostPortOptions + list(args)
        if os.name != "nt":
            cmd_line = [" ".join(cmd_line)]
        return subprocess.Popen(cmd_line, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def device_serial(self):
        if not self.default_serial:
            devices = self.devices()
            if devices:
                if len(devices):
                    self.default_serial = list(devices.keys())[0]
                else:
                    raise EnvironmentError("not device found.")
            else:
                raise EnvironmentError("Device not attached.")
        return self.default_serial

    def devices(self):
        '''get a dict of attached devices. key is the device serial, value is device name.'''
        out = self.raw_cmd("devices").communicate()[0].decode("utf-8")
        match = "List of devices attached"
        index = out.find(match)
        if index < 0:
            raise EnvironmentError("adb is not working.")
        return dict([s.split("\t") for s in out[index + len(match):].strip().splitlines() if s.strip()])

    def forward(self, local_port, device_port):
        '''adb port forward. return 0 if success, else non-zero.'''
        return self.cmd("forward", "tcp:%s" % local_port, "tcp:%s" % device_port).wait()
    
    def forward_localabstract(self,local_port, localabstract):
        '''adb port forward. return 0 if success, else non-zero.'''
        return self.cmd("forward", "tcp:%s" % local_port, localabstract).wait()

    def forward_list(self):
        '''adb forward --list'''
        version = self.version()
        if int(version[1]) <= 1 and int(version[2]) <= 0 and int(version[3]) < 31:
            raise EnvironmentError("Low adb version.")
        lines = self.raw_cmd("forward", "--list").communicate()[0].decode("utf-8").strip().splitlines()
        return [line.strip().split() for line in lines]
      
    def remove_forward_port(self,port):
        self.cmd("forward", "--remove", "tcp:%s" % port).wait()

    def version(self):
        '''adb version'''
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", self.raw_cmd("version").communicate()[0].decode("utf-8"))
        return [match.group(i) for i in range(4)]
    
    def getVersionCode(self, packageName):
        '''adb dumpsys package myPackageName'''
        versionCode = 0
        try:
            out = self.cmd('shell','dumpsys', 'package', packageName).communicate()[0]
            for line in out.strip().splitlines():
                tmp = line.strip()
                if tmp.startswith("versionCode="):
                    versionCode = int(tmp.split(" ")[0].split("=")[1])
                    break
        except:
            pass
        return versionCode
    
    def current_app(self):
        '''return packagename activity'''
        out = self.cmd('shell','dumpsys', 'window', 'w').communicate()[0] 
        flag = False
        packageName = None
        for line in out.strip().splitlines():
            if 'mCurrentFocus' in line:
                current_info = line[:-1].split(" ")[4]
                if "/" in current_info:
                    return (current_info.split('/')[0],current_info.split('/')[1])
                else:
                    if current_info.split('/')[0] == "StatusBar":
                        return (current_info.split('/')[0],None)
                    else:
                        flag = True
                        packageName = current_info.split('/')[0] 
            if flag and "mFocusedApp" in line:
                return (packageName, line[line.find(packageName)+len(packageName)+1:].split(" ")[0])
    
    def start_app(self, package_activity):
        '''start app'''
        self.cmd('shell','am', 'start', package_activity).wait()
    
    def shell(self, *args, **kwargs):
        '''adb shell command'''
        self.cmd(*['shell'] + list(args)).wait()
        
    def force_stop(self, packageName):
        '''force stop package'''
        self.shell('am','force-stop', packageName)
    
    def stop_third_app(self, ignore_filter=["com.tencent.mm"]):
        '''force stop third app'''
        ignore_filter_target = ['com.github.uiautomator','com.github.uiautomator.test']
        ignore_filter_target += ignore_filter
        for line in self.cmd('shell','pm','list','package','-3').communicate()[0].strip().splitlines():
            if 'package:' in line:
                package_name = line[len('package:'):]
                if not package_name in ignore_filter_target:
                    self.force_stop(package_name)

_init_local_port = LOCAL_PORT - 1


def next_local_port(adbHost=None):
    def is_port_listening(port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex((str(adbHost) if adbHost else '127.0.0.1', port))
        s.close()
        return result == 0
    global _init_local_port
    _init_local_port = _init_local_port + 1 if _init_local_port < 32764 else LOCAL_PORT
    while is_port_listening(_init_local_port):
        _init_local_port += 1
    return _init_local_port


class NotFoundHandler(object):

    '''
    Handler for UI Object Not Found exception.
    It's a replacement of UiAutomator watcher on device side.
    '''

    def __init__(self):
        self.__handlers = collections.defaultdict(lambda: {'on': True, 'handlers': []})

    def __get__(self, instance, type):
        return self.__handlers[instance.adb.device_serial()]


class AutomatorServer(object):

    """start and quit rpc server on device.
    """
    __jar_files = {
        "bundle.jar": "libs/bundle.jar",
        "uiautomator-stub.jar": "libs/uiautomator-stub.jar"
    }

    __apk_files = ["libs/app-uiautomator.apk", "libs/app-uiautomator-test.apk"]

    __sdk = 0

    handlers = NotFoundHandler()  # handler UI Not Found exception

    def __init__(self, serial=None, local_port=None, device_port=None, adb_server_host=None, adb_server_port=None):
        self.uiautomator_process = None
        self.adb = Adb(serial=serial, adb_server_host=adb_server_host, adb_server_port=adb_server_port)
        self.device_port = int(device_port) if device_port else DEVICE_PORT
        if local_port:
            self.local_port = local_port
        else:
            try:  # first we will try to use the local port already adb forwarded
                for s, lp, rp in self.adb.forward_list():
                    if s == self.adb.device_serial() and rp == 'tcp:%s'%self.device_port:
                        self.local_port = int(lp[4:])
                        break
                else:
                    self.local_port = next_local_port(adb_server_host)
            except:
                self.local_port = next_local_port(adb_server_host)
        self.wait_time = 0
        
    def set_think_time(self, wait_time):
        self.wait_time = wait_time

    def push(self):
        base_dir = os.path.dirname(__file__)
        for jar, url in self.__jar_files.items():
            filename = os.path.join(base_dir, url)
            self.adb.cmd("push", filename, "/data/local/tmp/").wait()
        return list(self.__jar_files.keys())

    def install(self):
        base_dir = os.path.dirname(__file__)
        for apk in self.__apk_files:
            self.adb.cmd("install", "-r", "-t", os.path.join(base_dir, apk)).wait()

    @property
    def jsonrpc(self):
        if self.wait_time != 0:
            time.sleep(self.wait_time)
        return self.jsonrpc_wrap(timeout=int(os.environ.get("jsonrpc_timeout", 90)))

    def jsonrpc_wrap(self, timeout):
        server = self
        ERROR_CODE_BASE = -32000

        def _JsonRPCMethod(url, method, timeout, restart=True):
            _method_obj = JsonRPCMethod(url, method, timeout)

            def wrapper(*args, **kwargs):
                URLError = urllib3.exceptions.HTTPError if os.name == "nt" else urllib2.URLError
                try:
                    return _method_obj(*args, **kwargs)
                except (URLError, socket.error, HTTPException) as e:
                    if restart:
                        server.stop()
                        server.start(timeout=30)
                        return _JsonRPCMethod(url, method, timeout, False)(*args, **kwargs)
                    else:
                        raise
                except JsonRPCError as e:
                    if e.code >= ERROR_CODE_BASE - 1:
                        server.stop()
                        server.start()
                        return _method_obj(*args, **kwargs)
                    elif e.code == ERROR_CODE_BASE - 2 and self.handlers['on']:  # Not Found
                        try:
                            self.handlers['on'] = False
                            # any handler returns True will break the left handlers
                            any(handler(self.handlers.get('device', None)) for handler in self.handlers['handlers'])
                        finally:
                            self.handlers['on'] = True
                        return _method_obj(*args, **kwargs)
                    raise
            return wrapper

        return JsonRPCClient(self.rpc_uri,
                             timeout=timeout,
                             method_class=_JsonRPCMethod)

    def __jsonrpc(self):
        return JsonRPCClient(self.rpc_uri, timeout=int(os.environ.get("JSONRPC_TIMEOUT", 90)))

    def sdk_version(self):
        '''sdk version of connected device.'''
        if self.__sdk == 0:
            try:
                self.__sdk = int(self.adb.cmd("shell", "getprop", "ro.build.version.sdk").communicate()[0].decode("utf-8").strip())
            except:
                pass
        return self.__sdk
    
    def start(self,timeout=5):
        '''add retry 2 times'''
        try:
            time.sleep(4) # startup delay 4 seconds
            self._start(timeout)
        except:
            self.stop()
            time.sleep(4)
            self._start(timeout)
            
    def _start(self, timeout=5):
        sdk = self.sdk_version()
        if sdk != 0 and sdk < 18:
            files = self.push()
            cmd = list(itertools.chain(
                ["shell", "uiautomator", "runtest"],
                files,
                ["-c", "com.github.uiautomatorstub.Stub"],
                ["--nohup"]
            ))
        else:
            if self.checkVersion():
                self.install()
            cmd = ["shell", "am", "instrument", "-w",
                   "com.github.uiautomator.test/android.support.test.runner.AndroidJUnitRunner&"]  
        self.uiautomator_process = self.adb.cmd(*cmd)
        self.adb.forward(self.local_port, self.device_port)
        time.sleep(4)
        while not self.alive and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1
        if not self.alive:
            raise IOError("RPC server not started!")

    def ping(self):
        try:
            return self.__jsonrpc().ping()
        except:
            pass
    
    def checkVersion(self):
        ''' check uiautomator apk version '''
        version_code = self.adb.getVersionCode('com.github.uiautomator')
        return True if u2_version_code > version_code else False

    @property
    def alive(self):
        '''Check if the rpc server is alive.'''
        return self.ping() == "pong"

    def stop(self):
        '''Stop the rpc server.'''
        if self.uiautomator_process and self.uiautomator_process.poll() is None:
            res = None
            try:
                res = urllib2.urlopen(self.stop_uri)
                self.uiautomator_process.wait()
            except:
                self.uiautomator_process.kill()
            finally:
                if res is not None:
                    res.close()
                self.uiautomator_process = None
        try:
            out = self.adb.cmd("shell", "ps", "-C", "uiautomator").communicate()[0].decode("utf-8").strip().splitlines()
            if out:
                index = out[0].split().index("PID")
                for line in out[1:]:
                    if len(line.split()) > index:
                        self.adb.cmd("shell", "kill", "-9", line.split()[index]).wait()
        except:
            pass
        try:
            self.adb.cmd("shell", "am", "force-stop", 'com.github.uiautomator').wait()
        except:
            pass
            

    @property
    def stop_uri(self):
        return "http://%s:%d/stop" % (self.adb.adb_server_host, self.local_port)

    @property
    def rpc_uri(self):
        return "http://%s:%d/jsonrpc/0" % (self.adb.adb_server_host, self.local_port)

    @property
    def screenshot_uri(self):
        return "http://%s:%d/screenshot/0" % (self.adb.adb_server_host, self.local_port)
    

    def screenshot(self, filename=None, scale=1.0, quality=100):
        if self.sdk_version() >= 18:
            try:
                req = urllib2.Request("%s?scale=%s&quality=%s" % (self.screenshot_uri, scale, quality))
                result = urllib2.urlopen(req, timeout=30)
                if filename:
                    with open(filename, 'wb') as f:
                        f.write(result.read())
                        return filename
                else:
                    return result.read()
            except:
                pass
        return None


class AutomatorDevice(object):

    '''uiautomator wrapper of android device'''

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

    def __init__(self, serial=None, local_port=None, adb_server_host=None, adb_server_port=None):
        self.server = AutomatorServer(
            serial=serial,
            local_port=local_port,
            adb_server_host=adb_server_host,
            adb_server_port=adb_server_port
        )
        self.adb = self.server.adb
        self.webdriver = None
    
    def set_think_time(self,wait_time):
        '''uiautomator steps wait time'''
        self.server.set_think_time(wait_time)

    def __call__(self, **kwargs):
        return AutomatorDeviceObject(self, Selector(**kwargs))

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

    def long_click(self, x, y, duration=0):
        '''long click at arbitrary coordinates.'''
        return self.server.jsonrpc.long_click(x, y, duration)

    def swipe(self, sx, sy, ex, ey, steps=100):
        return self.server.jsonrpc.swipe(sx, sy, ex, ey, steps)

    def swipePoints(self, points, steps=100):
        ppoints = []
        for p in points:
            ppoints.append(p[0])
            ppoints.append(p[1])
        return self.server.jsonrpc.swipePoints(ppoints, steps)

    def drag(self, sx, sy, ex, ey, steps=100):
        '''Swipe from one point to another point.'''
        return self.server.jsonrpc.drag(sx, sy, ex, ey, steps)

    def dump(self, filename=None, compressed=True, pretty=True):
        '''dump device window and pull to local file.'''
        content = self.server.jsonrpc.dumpWindowHierarchy(compressed, None)
        if filename:
            with open(filename, "wb") as f:
                f.write(content.encode("utf-8"))
        if pretty and "\n " not in content:
            xml_text = xml.dom.minidom.parseString(content.encode("utf-8"))
            content = U(xml_text.toprettyxml(indent='  '))
        return content

    def screenshot(self, filename=None, scale=1.0, quality=100):
        '''take screenshot.'''
        result = self.server.screenshot(filename, scale, quality)
        if result:
            return result
        if filename is None:
            filename = tempfile.mktemp()
        png = "/data/local/tmp/screen_shot.png"
        self.server.adb.cmd("shell", "screencap", "-p", png).wait()
        self.server.adb.cmd("pull", png, filename).wait()
        self.server.adb.cmd("shell", "rm", png).wait()
        if os.path.exists(filename):
            with open(filename,'rb') as f:
                return f.read()

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
    
    def set_text(self, content):
        '''shell input set test'''
        self.adb.shell('input text %s'%content)

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
    def handlers(self):
        obj = self

        class Handlers(object):

            def on(self, fn):
                if fn not in obj.server.handlers['handlers']:
                    obj.server.handlers['handlers'].append(fn)
                obj.server.handlers['device'] = obj
                return fn

            def off(self, fn):
                if fn in obj.server.handlers['handlers']:
                    obj.server.handlers['handlers'].remove(fn)

        return Handlers()

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
        def _press(key, meta=None, num=1):
            if isinstance(key, int):
                return self.server.jsonrpc.pressKeyCode(key, meta) if meta else self.server.jsonrpc.pressKeyCode(key)
            else:
                if key == "back":
                    return self.back(num)
                return self.server.jsonrpc.pressKey(str(key))
        return _press
    
    def back(self, num=1):
        '''force back'''
        def _back():
            self.adb.shell("input keyevent 4")
        while num>0:
            t = threading.Thread(target=_back)
            t.setDaemon(True)
            t.start()
            time.sleep(0.2)
            num -= 1

    def wakeup(self):
        '''turn on screen in case of screen off.'''
        self.server.jsonrpc.wakeUp()

    def sleep(self):
        '''turn off screen in case of screen on.'''
        self.server.jsonrpc.sleep()
    
    def start_activity(self, packageActivity):
        '''start activity'''
        self.adb.start_app(packageActivity)
    
    def wait_time(self, wait_time):
        '''wait time relate python sleep'''
        time.sleep(wait_time)

    @property
    def screen(self):
        '''
        Turn on/off screen.
        Usage:
        d.screen.on()
        d.screen.off()

        d.screen == 'on'  # Check if the screen is on, same as 'd.screenOn'
        d.screen == 'off'  # Check if the screen is off, same as 'not d.screenOn'
        '''
        devive_self = self

        class _Screen(object):
            def on(self):
                return devive_self.wakeup()

            def off(self):
                return devive_self.sleep()

            def __call__(self, action):
                if action == "on":
                    return self.on()
                elif action == "off":
                    return self.off()
                else:
                    raise AttributeError("Invalid parameter: %s" % action)

            def __eq__(self, value):
                info = devive_self.info
                if "screenOn" not in info:
                    raise EnvironmentError("Not supported on Android 4.3 and belows.")
                if value in ["on", "On", "ON"]:
                    return info["screenOn"]
                elif value in ["off", "Off", "OFF"]:
                    return not info["screenOn"]
                raise ValueError("Invalid parameter. It can only be compared with on/off.")

            def __ne__(self, value):
                return not self.__eq__(value)

        return _Screen()

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
            if timeout / 1000 + 5 > int(os.environ.get("JSONRPC_TIMEOUT", 90)):
                http_timeout = timeout / 1000 + 5
            else:
                http_timeout = int(os.environ.get("JSONRPC_TIMEOUT", 90))
            if action == "idle":
                return self.server.jsonrpc_wrap(timeout=http_timeout).waitForIdle(timeout)
            elif action == "update":
                return self.server.jsonrpc_wrap(timeout=http_timeout).waitForWindowUpdate(package_name, timeout)
        return _wait

    def exists(self, **kwargs):
        '''Check if the specified ui object by kwargs exists.'''
        return self(**kwargs).exists
    
    def stop_third_app(self,ignore_filter=["com.tencent.mm"]):
        '''停止第三方app'''
        self.adb.stop_third_app(ignore_filter)
    
    @property
    def configurator(self):
        '''
        :Args:
            actionAcknowledgmentTimeout, default:3000ms
            keyInjectionDelay, default:0ms
            scrollAcknowledgmentTimeout, default: 200ms
            waitForIdleTimeout default: 10000ms
            waitForSelectorTimeout default: 10000ms
        :Usage:
            d.configurator.set()
            d.configurator.info()
            d.configurator.restore()
        '''
        device.self = self
        class _ConfiguratorInfo(object):
            def info(self):
                return device.self.server.jsonrpc.getConfigurator()
            def set(self, **kwargs):
                config_info = {}
                for k in kwargs:
                    config_info[k] = kwargs[k]
                return device.self.server.jsonrpc.setConfigurator(config_info)
            def restore(self): 
                return device.self.server.jsonrpc.setConfigurator({'flag':True})
        return _ConfiguratorInfo()
    
    @property
    def toast(self):
        device_self = self
        class _Toast(object):
            def on(self):
                return device_self.server.jsonrpc.toast('on')
            def off(self):
                return device_self.server.jsonrpc.toast('off')
        return _Toast()
    
    @property
    def img_tz(self):
        device_self = self
        class _Img(object):
            def exists(self, query, origin=None, interval=2, timeout=4, algorithm='sift', threshold=0.75, colormode=0):
                if origin:
                    try:
                        pos = ImageUtil.find_image_positon(query, origin, algorithm, threshold,colormode)
                        if pos:
                            return True
                    except:
                        pass
                    return False
                begin = time.time()
                isExists = False
                src_img_path = tempfile.mktemp()
                device_self.screenshot(src_img_path)
                while (time.time() - begin < timeout):
                    time.sleep(interval)
                    device_self.screenshot(src_img_path)
                    try:
                        pos = ImageUtil.find_image_positon(query, src_img_path, algorithm, threshold, colormode)
                        if pos:
                            isExists = True  
                    except:
                        pass
                    if not isExists:
                        time.sleep(interval)
                        del_file(src_img_path)
                        continue
                    del_file(src_img_path)
                    return isExists
             
            def click(self, query, origin=None, algorithm='sift', threshold=0.75, colormode=0):
                pos = self.get_location(query, origin, algorithm, threshold, colormode)
                if pos:
                    device_self.click(pos[0],pos[1])
                else:
                    raise AssertionError("not find sub img on big img") 
                
            def get_location(self, query, origin=None, algorithm='sift', threshold=0.75, colormode=0):
                src_img_path = origin 
                if src_img_path is None:
                    src_img_path = tempfile.mktemp()
                    device_self.screenshot(src_img_path)
                if not os.path.exists(src_img_path):
                    raise IOError('path not origin img')
                try:
                    pos = ImageUtil.find_image_positon(query, src_img_path, algorithm, threshold, colormode)
                    return pos 
                except:
                    raise
                finally:
                    if origin is None:
                        del_file(src_img_path)
            
        return _Img()
    
    @property
    def img(self):
        device_self = self
        class _Img(object):
            def exists(self, query, origin=None, interval=2, timeout=4, threshold=0.99,colormode=0):
                threshold = 1 - threshold
                if origin:
                    return isMatch(query, origin, threshold,colormode)
                begin = time.time()
                isExists = False
                tmp = tempfile.mktemp()
                while (time.time() - begin < timeout):
                    device_self.screenshot(tmp)
                    isExists = isMatch(query, tmp, threshold,colormode)
                    if not isExists:
                        time.sleep(interval)
                        del_file(tmp)
                        continue
                    del_file(tmp)
                    return isExists
                
            def click(self, query, origin=None, threshold=0.99, rotation=0,colormode=0):
                threshold = 1 - threshold
                pos = self.get_location(query, origin, threshold, rotation, colormode)
                if pos:
                    device_self.click(pos[0], pos[1])
                else:
                    raise AssertionError("not find sub img on big img") 
       
            def get_location(self, query, origin=None, threshold=0.99, rotation=0, colormode=0):
                threshold = 1 - threshold
                src_img_path = origin 
                if src_img_path is None:
                    src_img_path = tempfile.mktemp()
                    device_self.screenshot(src_img_path)
                if not os.path.exists(src_img_path):
                    raise IOError('path not origin img')
                try:
                    pos = getMatchedCenterOffset(query, src_img_path, threshold, rotation, colormode)
                    return pos
                except:
                    raise
                finally:
                    if origin is None:
                        del_file(src_img_path)
        return _Img()
    
    @property
    def webview(self):
        if self.webdriver:
            return self.webdriver
        self.webdriver = ChromeDriver(self)
        return self.webdriver 
    
    def quit(self):
        self.server.stop()
        try:
            if self.webdriver:
                self.webdriver.quit()
        except:
            pass
        
        
    def touchAction(self):
        device_self = self
        class _TouchAction(object):
            def __init__(self):
                self._actions = []
                self._x = 0
                self._y = 0    
            def down(self,x,y):
                self._add_action("touchDown", self._get_optx({'x':x,'y':y}))
                return self        
            def up(self):
                self._add_action("touchUp", {'x':self._x,'y':self._y})
                return self
            def move_to(self,x,y):
                self._add_action("moveTo", self._get_optx({'x':x,'y':y}))
                return self
            def wait(self,ms):
                self._add_action("wait", {'s':ms})
                return self
            def _add_action(self, action, options):
                gesture = {
                    'action': action,
                    'options': options,
                }
                self._actions.append(gesture)
            def _get_optx(self, opt):
                self._x = opt['x']
                self._y = opt['y']
                return opt
                
            def perform(self):
                try:
                    for action in self._actions:
                        act = action.get('action')
                        opt = action.get('options')
                        if act == "touchDown":
                            device_self.server.jsonrpc.touchDown(opt['x'],opt['y'])
                        if act == "moveTo":
                            device_self.server.jsonrpc.moveTo(opt['x'],opt['y'])
                        if act == "touchUp":
                            device_self.server.jsonrpc.touchUp(opt['x'],opt['y'])
                        if act == "wait":
                            ms = opt.get("s")
                            time.sleep(ms)
                finally:
                    self._actions = []

        return _TouchAction()
    
        
def del_file(path):
    if os.path.exists(path): 
        os.remove(path)

Device = AutomatorDevice


class AutomatorDeviceUiObject(object):

    '''Represent a UiObject, on which user can perform actions, such as click, set text
    '''

    __alias = {'description': "contentDescription"}

    def __init__(self, device, selector):
        self.device = device
        self.jsonrpc = device.server.jsonrpc
        self.selector = selector

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
    
    def long_press(self, duration=0):
        '''long press obj'''
        return self.jsonrpc.longClick(self.selector, duration)
        

    @property
    def long_click(self):
        '''
        Perform a long click action on the object.
        Usage:
        d(text="Image").long_click()  # long click on the center of the ui object
        d(text="Image").long_click.topleft()  # long click on the topleft of the ui object
        d(text="Image").long_click.bottomright()  # long click on the topleft of the ui object
        '''
        @param_to_property(corner=["tl", "topleft", "br", "bottomright", "wait"])
        def _long_click(corner=None, duration=0):
            info = self.info
            if info["longClickable"]:
                if corner in ["tl", "topleft", "br", "bottomright"]:
                    return self.jsonrpc.longClick(self.selector, corner)
                else:
                    return self.jsonrpc.longClick(self.selector, duration)
            else:
                bounds = info.get("visibleBounds") or info.get("bounds")
                if corner in ["tl", "topleft"]:
                    x = (5 * bounds["left"] + bounds["right"]) / 6
                    y = (5 * bounds["top"] + bounds["bottom"]) / 6
                elif corner in ["br", "bottomright"]:
                    x = (bounds["left"] + 5 * bounds["right"]) / 6
                    y = (bounds["top"] + 5 * bounds["bottom"]) / 6
                else:
                    x = (bounds["left"] + bounds["right"]) / 2
                    y = (bounds["top"] + bounds["bottom"]) / 2
                return self.device.long_click(x, y, duration)
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
            ctp = lambda pt: point(*pt) if type(pt) == tuple else pt  # convert tuple to point
            s1, s2, e1, e2 = ctp(start1), ctp(start2), ctp(end1), ctp(end2)
            return self.jsonrpc.gesture(self.selector, s1, s2, e1, e2, steps)
        obj = type("Gesture", (object,), {"to": to})()
        return obj if len(args) == 0 else to(None, *args, **kwargs)

    def gestureM(self, start1, start2, start3, *args, **kwargs):
        '''
        perform 3 point gesture.
        Usage:
        d().gestureM((100,200),(100,300),(100,400),(100,400),(100,400),(100,400))
        d().gestureM((100,200),(100,300),(100,400)).to((100,400),(100,400),(100,400))
        '''
        def to(obj_self, end1, end2, end3, steps=100):
            ctp = lambda pt: point(*pt) if type(pt) == tuple else pt  # convert tuple to point
            s1, s2, s3, e1, e2, e3 = ctp(start1), ctp(start2), ctp(start3), ctp(end1), ctp(end2), ctp(end3)
            return self.jsonrpc.gesture(self.selector, s1, s2, s3, e1, e2, e3, steps)
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
        Perform swipe action. if device platform greater than API 18, percent can be used and value between 0 and 1
        Usages:
        d().swipe.right()
        d().swipe.left(steps=10)
        d().swipe.up(steps=10)
        d().swipe.down()
        d().swipe("right", steps=20)
        d().swipe("right", steps=20, percent=0.5)
        '''
        @param_to_property(direction=["up", "down", "right", "left"])
        def _swipe(direction="left", steps=10, percent=1):
            if percent == 1:
                return self.jsonrpc.swipe(self.selector, direction, steps)
            else:
                return self.jsonrpc.swipe(self.selector, direction, percent, steps)
        return _swipe

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
            if timeout / 1000 + 5 > int(os.environ.get("JSONRPC_TIMEOUT", 90)):
                http_timeout = timeout / 1000 + 5
            else:
                http_timeout = int(os.environ.get("JSONRPC_TIMEOUT", 90))
            method = self.device.server.jsonrpc_wrap(
                timeout=http_timeout
            ).waitUntilGone if action == "gone" else self.device.server.jsonrpc_wrap(timeout=http_timeout).waitForExists
            return method(self.selector, timeout)
        return _wait
    
    def screenshot(self,filename=None, scale=1.0, quality=100):
        '''element screen shot'''
        result = self.jsonrpc.screenshot(self.selector, scale, quality)
        if filename is None:
            filename = tempfile.mktemp()
        with open(filename, 'wb') as f:
            f.write(result)
        return filename

class AutomatorDeviceNamedUiObject(AutomatorDeviceUiObject):

    def __init__(self, device, name):
        super(AutomatorDeviceNamedUiObject, self).__init__(device, name)

    def child(self, **kwargs):
        return AutomatorDeviceNamedUiObject(
            self.device,
            self.jsonrpc.getChild(self.selector, Selector(**kwargs))
        )

    def sibling(self, **kwargs):
        return AutomatorDeviceNamedUiObject(
            self.device,
            self.jsonrpc.getFromParent(self.selector, Selector(**kwargs))
        )


class AutomatorDeviceObject(AutomatorDeviceUiObject):

    '''Represent a generic UiObject/UiScrollable/UiCollection,
    on which user can perform actions, such as click, set text
    '''

    def __init__(self, device, selector):
        super(AutomatorDeviceObject, self).__init__(device, selector)

    def child(self, **kwargs):
        '''set childSelector.'''
        return AutomatorDeviceObject(
            self.device,
            self.selector.clone().child(**kwargs)
        )

    def sibling(self, **kwargs):
        '''set fromParent selector.'''
        return AutomatorDeviceObject(
            self.device,
            self.selector.clone().sibling(**kwargs)
        )

    child_selector, from_parent = child, sibling

    def child_by_text(self, txt, **kwargs):
        if "allow_scroll_search" in kwargs:
            allow_scroll_search = kwargs.pop("allow_scroll_search")
            name = self.jsonrpc.childByText(
                self.selector,
                Selector(**kwargs),
                txt,
                allow_scroll_search
            )
        else:
            name = self.jsonrpc.childByText(
                self.selector,
                Selector(**kwargs),
                txt
            )
        return AutomatorDeviceNamedUiObject(self.device, name)

    def child_by_description(self, txt, **kwargs):
        if "allow_scroll_search" in kwargs:
            allow_scroll_search = kwargs.pop("allow_scroll_search")
            name = self.jsonrpc.childByDescription(
                self.selector,
                Selector(**kwargs),
                txt,
                allow_scroll_search
            )
        else:
            name = self.jsonrpc.childByDescription(
                self.selector,
                Selector(**kwargs),
                txt
            )
        return AutomatorDeviceNamedUiObject(self.device, name)

    def child_by_instance(self, inst, **kwargs):
        return AutomatorDeviceNamedUiObject(
            self.device,
            self.jsonrpc.childByInstance(self.selector, Selector(**kwargs), inst)
        )

    @property
    def count(self):
        return self.jsonrpc.count(self.selector)

    def __len__(self):
        return self.count

    def __getitem__(self, index):
        count = self.count
        if index >= count:
            raise IndexError()
        elif count == 1:
            return self
        else:
            selector = self.selector.clone()
            selector["instance"] = index
            return AutomatorDeviceObject(self.device, selector)

    def __iter__(self):
        obj, length = self, self.count

        class Iter(object):

            def __init__(self):
                self.index = -1

            def next(self):
                self.index += 1
                if self.index < length:
                    return obj[self.index]
                else:
                    raise StopIteration()
            __next__ = next

        return Iter()

    def right(self, **kwargs):
        def onrightof(rect1, rect2):
            left, top, right, bottom = intersect(rect1, rect2)
            return rect2["left"] - rect1["right"] if top < bottom else -1
        return self.__view_beside(onrightof, **kwargs)

    def left(self, **kwargs):
        def onleftof(rect1, rect2):
            left, top, right, bottom = intersect(rect1, rect2)
            return rect1["left"] - rect2["right"] if top < bottom else -1
        return self.__view_beside(onleftof, **kwargs)

    def up(self, **kwargs):
        def above(rect1, rect2):
            left, top, right, bottom = intersect(rect1, rect2)
            return rect1["top"] - rect2["bottom"] if left < right else -1
        return self.__view_beside(above, **kwargs)

    def down(self, **kwargs):
        def under(rect1, rect2):
            left, top, right, bottom = intersect(rect1, rect2)
            return rect2["top"] - rect1["bottom"] if left < right else -1
        return self.__view_beside(under, **kwargs)

    def __view_beside(self, onsideof, **kwargs):
        bounds = self.info["bounds"]
        min_dist, found = -1, None
        for ui in AutomatorDeviceObject(self.device, Selector(**kwargs)):
            dist = onsideof(bounds, ui.info["bounds"])
            if dist >= 0 and (min_dist < 0 or dist < min_dist):
                min_dist, found = dist, ui
        return found

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

device = AutomatorDevice()
