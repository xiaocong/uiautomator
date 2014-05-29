#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import re
import sys
import random
from collections import namedtuple
import xml.etree.ElementTree as etree

from uiautomator import device as d, intersect


def u(x):
    if sys.version_info.major == 2:
        return x.decode('utf-8') if type(x) is str else x
    elif sys.version_info.major == 3:
        return x

Bounds = namedtuple('Bounds', ['left', 'top', 'right', 'bottom'])


class UINode(object):

    dict_sel2xml_simple = {
        'text':                  ['text', u],
        'className':             ['class', u],
        'description':           ['content-desc', u],
        'checkable':             ['checkable', lambda s: s == 'true'],
        'checked':               ['checked', lambda s: s == 'true'],
        'clickable':             ['clickable', lambda s: s == 'true'],
        'longClickable':         ['long-clickable', lambda s: s == 'true'],
        'scrollable':            ['scrollable', lambda s: s == 'true'],
        'enabled':               ['enabled', lambda s: s == 'true'],
        'focusable':             ['focusable', lambda s: s == 'true'],
        'focused':               ['focused', lambda s: s == 'true'],
        'selected':              ['selected', lambda s: s == 'true'],
        'packageName':           ['package', u],
        'resourceId':            ['resource-id', u],
        'index':                 ['index', int]
    }

    def __init__(self, node, root=None):
        self.node = node
        self.root = root
        bounds = self.node_bounds(node)
        self.bounds = Bounds(left=bounds['left'],
                             top=bounds['top'],
                             right=bounds['right'],
                             bottom=bounds['bottom'])

        def onrightof(rect1, rect2):
            left, top, right, bottom = intersect(rect1, rect2)
            return rect2["left"] - rect1["right"] if top < bottom else -1

        def onleftof(rect1, rect2):
            left, top, right, bottom = intersect(rect1, rect2)
            return rect1["left"] - rect2["right"] if top < bottom else -1

        def above(rect1, rect2):
            left, top, right, bottom = intersect(rect1, rect2)
            return rect1["top"] - rect2["bottom"] if left < right else -1

        def under(rect1, rect2):
            left, top, right, bottom = intersect(rect1, rect2)
            return rect2["top"] - rect1["bottom"] if left < right else -1

        def besideof(onsideof):
            min_dist, found = -1, None
            for n in root.iter('node'):
                dist = onsideof(bounds, self.node_bounds(n))
                if dist >= 0 and (min_dist < 0 or dist < min_dist) and \
                   (node.get('text') or node.get('content-desc')):
                    min_dist, found = dist, n
            if found is not None:
                if found.get('class').endswith('EditText'):
                    return ('', found.get('content-desc'), found.get('class'))
                else:
                    return (found.get('text'), found.get('content-desc'), found.get('class'))
            else:
                return None

        self.sides = Bounds(left=besideof(onleftof),
                            top=besideof(above),
                            right=besideof(onrightof),
                            bottom=besideof(under))

    def __eq__(self, other):
        attrs = ['class', 'content-desc', 'checkable', 'checked', 'clickable', 'long-clickable',
                 'scrollable', 'enabled', 'focusable', 'package', 'resource-id']
        if any(self.node.get(attr) != other.node.get(attr) for attr in attrs):
            return False
        if not self.node.get('class').endswith('EditText') and \
           self.node.get('text') != other.node.get('text'):
            return False
        if self.node.get('text') == '' and self.node.get('content-desc') == '' and self.sides != other.sides:
            return False
        return True

    @classmethod
    def same(clz, n1, n2, ignores=['bounds', 'instance']):
        '''compare two xml nodes'''
        return all(n1.get(key) == n2.get(key) for key in n1.keys() if key not in ignores)

    @classmethod
    def node_to_selector(clz, node):
        '''convert a XML node to selector'''
        def traverse():
            node_keys = node.keys()
            for key, (key_node, func_convert) in clz.dict_sel2xml_simple.items():
                if key_node in node_keys:
                    value = func_convert(node.get(key_node))
                    if value not in ['', None]:
                        yield (key, value)
        sel = dict(traverse())
        sel['instance'] = node.get('instance') or 0
        return sel

    @classmethod
    def node_bounds(clz, node):
        match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.get('bounds'))
        return {
            'top': int(match.group(2)),
            'left': int(match.group(1)),
            'bottom': int(match.group(4)),
            'right': int(match.group(3))
        }

    @property
    def width(self):
        return self.bounds.right - self.bounds.left

    @property
    def height(self):
        return self.bounds.bottom - self.bounds.top

    @property
    def selector(self):
        return self.node_to_selector(self.node)

    @property
    def operatable(self):
        if self.node.get('enabled') == 'false':
            return False
        if self.node.get('class').endswith('EditText'):
            return True
        attrs = ['checkable', 'clickable', 'long-clickable', 'scrollable', 'focusable']
        return any(self.node.get(attr) == 'true' for attr in attrs)

    def __getattr__(self, attr):
        attrs = {
            'checkable': 'checkable',
            'clickable': 'clickable',
            'long_clickable': 'long-clickable',
            'scrollable': 'scrollable',
            'focusable': 'focusable'
        }
        if attr == 'editable':
            return self.node.get('class').endswith('EditText')
        elif attr in attrs:
            return self.node.get(attrs[attr]) == 'true'
        else:
            raise AttributeError()

    def __str__(self):
        if sys.version_info.major == 2:
            return (u"%s: %s" % (self.node.get('class'), self.node.get('text'))).encode('utf-8')
        else:
            return "%s: %s" % (self.node.get('class'), self.node.get('text'))


def rootxml_add_instance(root):
    '''add instance property to xml nodes'''
    for f in root.iter('node'):
        i = 0
        for s in root.iter('node'):
            if UINode.same(f, s):
                i += 1
            elif s is f:
                f.set('instance', i)
                break
    return root


def rootxml():
    '''return the root nodes with instance id'''
    return rootxml_add_instance(etree.fromstring(d.dump().encode("utf-8")))


def click(node):
    d.wait.idle()
    return d(**node.selector).exists and d(**node.selector).click()


def long_click(node):
    d.wait.idle()
    return d(**node.selector).exists and d(**node.selector).long_click()


def edit(node):
    d.wait.idle()
    return d(**node.selector).exists and d(**node.selector).set_text('123456')


def scroll(node):
    d.wait.idle()
    if d(**node.selector).exists:
        if not d(**node.selector).scroll.horiz.forward(steps=10):
            d(**node.selector).scroll.horiz.backward(steps=10)
        if not d(**node.selector).scroll.vert.forward(steps=10):
            d(**node.selector).scroll.vert.backward(steps=10)
        return True
    return False


Nodes = namedtuple('Nodes', ['clickable', 'editable', 'long_clickable', 'scrollable'])


def get_nodes():
    cols = Nodes([], [], [], [])
    root = rootxml()
    for node in root.iter('node'):
        ui = UINode(node, root)
        if ui.clickable or ui.checkable:
            cols.clickable.append(ui)
        if ui.editable:
            cols.editable.append(ui)
        if ui.long_clickable:
            cols.long_clickable.append(ui)
        if ui.scrollable:
            cols.scrollable.append(ui)
    return cols


def main():
    done = Nodes([], [], [], [])

    def perform(current, done, func, pre=None):
        for n in current:
            if n not in done and (pre is None or pre.bounds != n.bounds):
                try:
                    func(n)
                    done.append(n)
                    return n
                except:
                    pass
        return None
    pre = None
    while True:
        current = get_nodes()

        def do_op():
            node = perform(current.editable, done.editable, edit, pre) or \
                perform(current.clickable, done.clickable, click, pre) or \
                perform(current.long_clickable, done.long_clickable, long_click, pre)
            if node is None:
                for n in current.scrollable:
                    try:
                        scroll(n)
                    except:
                        pass
            return node

        now = do_op()
        if now:
            pre = now
        else:
            if not d.press.menu():
                d.press.back()
        d.wait.idle()

if __name__ == "__main__":
    main()
