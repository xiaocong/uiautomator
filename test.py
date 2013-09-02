#!/usr/bin/env python
# -*- coding: utf-8 -*-

from uiautomator import device as d


def unlock_screen():
    '''unlock screen on Android 4.3'''
    if d.info["currentPackageName"] == "android" and d(resourceId="android:id/glow_pad_view").exists:
        d(resourceId="android:id/glow_pad_view").swipe.down()
    d.wait.idle()

def main():
    d.screen.on()
    unlock_screen()
    for i in range(100):
        d.press.home()
        d(description="Apps").click()
        d(scrollable=True).scroll.horiz.toBeginning()
        d(scrollable=True).scroll.horiz.to(text="Bookmark")
        d(scrollable=True).scroll.horiz.forward()
        d(scrollable=True).fling.horiz.forward()
        d(scrollable=True).fling.horiz.toBeginning()
        d.press.back()
        d.press.search()
        d(resourceId="com.google.android.googlequicksearchbox:id/search_box").set_text("hello world!")
        d.press.enter()
        d.press.back()
        d.press.back()
        d.press.home()
        d(description="Apps").click()
        d(scrollable=True).scroll.horiz.toBeginning()
        d(scrollable=True).scroll.horiz.toBeginning()
        d(scrollable=True).scroll.horiz.to(text="Gallery")
        d(text="Gallery").click()
        d(resourceId="com.android.gallery3d:id/gl_root_view").click()
        d(resourceId="com.android.gallery3d:id/gl_root_view").click()
        d(resourceId="com.android.gallery3d:id/gl_root_view").pinch.Out()
        d(resourceId="com.android.gallery3d:id/gl_root_view").pinch.Out()
        d(resourceId="com.android.gallery3d:id/gl_root_view").pinch.In()
        d(resourceId="com.android.gallery3d:id/gl_root_view").pinch.In()
        for j in range(4):
            d.press("back")

if __name__ == "__main__":
    main()
