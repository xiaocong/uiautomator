#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from uiautomator import Selector


class TestSelector(unittest.TestCase):

    fields = {
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
    mask = "mask"

    def test_init(self):
        sel = Selector()
        self.assertEqual(sel[self.mask], 0)
        self.assertEqual(sel["childOrSibling"], [])
        self.assertEqual(sel["childOrSiblingSelector"], [])

    def test_add(self):
        for k, v in self.fields.items():
            kwargs = {k: v[1]}
            sel = Selector(**kwargs)
            self.assertEqual(sel[self.mask], v[0])

        for k1, v1 in self.fields.items():
            for k2, v2 in self.fields.items():
                if k1 != k2:
                    kwargs = {k1: v1[1], k2: v2[1]}
                    sel = Selector(**kwargs)
                    self.assertEqual(sel[self.mask], v1[0] | v2[0])

    def test_delete(self):
        for k, v in self.fields.items():
            kwargs = {k: v[1]}
            sel = Selector(**kwargs)
            del sel[k]
            self.assertEqual(sel[self.mask], 0)

        for k1, v1 in self.fields.items():
            for k2, v2 in self.fields.items():
                if k1 != k2:
                    kwargs = {k1: v1[1], k2: v2[1]}
                    sel = Selector(**kwargs)
                    del sel[k1]
                    self.assertEqual(sel[self.mask], v2[0])
                    del sel[k2]
                    self.assertEqual(sel[self.mask], 0)

    def test_error(self):
        with self.assertRaises(ReferenceError):
            Selector(text1="")

    def test_child_and_sibling(self):
        sel = Selector()
        sel.child(text="...")
        self.assertEqual(sel["childOrSibling"], ["child"])
        self.assertEqual(sel["childOrSiblingSelector"], [Selector(text="...")])

        sel.sibling(text="---")
        self.assertEqual(sel["childOrSibling"], ["child", "sibling"])
        self.assertEqual(sel["childOrSiblingSelector"], [Selector(text="..."), Selector(text="---")])

    def test_clone(self):
        kwargs = {
            "text": "1234",
            "description": "desc...",
            "clickable": True,
            "focusable": False,
            "packageName": "android"
        }
        sel = Selector(**kwargs)
        sel.child(text="1")
        sel.sibling(text="1")
        sel.child(text="1")

        clone = sel.clone()
        for k in kwargs:
            self.assertEqual(sel[k], clone[k])
        self.assertEqual(sel["childOrSibling"], clone["childOrSibling"])
        self.assertEqual(sel["childOrSiblingSelector"], clone["childOrSiblingSelector"])
