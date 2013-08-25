uiautomator
===========

This module is a Python wrapper of Android [uiautomator][] testing framework.

## Installation

    $ pip install uiautomator

## Usages

### Pre-requirements

- Install [Android SDK](http://developer.android.com/sdk/index.html), and set $ANDROID_HOME environment to the correct path.
- Enable ADB setting on device and connect your android device using usb with your PC.
- Set $ANDROID_SERIAL environment in case of multiple android devices connected.

### import uiautomator

```python
from uiautomator import device as d
```

**In below examples, we use `d` represent the android device object.**

### Retrieve the device info

```python
d.info
```

Below is a possible result:

```
{ u'displayRotation': 0,
  u'displaySizeDpY': 640,
  u'displaySizeDpX': 360,
  u'currentPackageName': u'com.android.launcher',
  u'productName': u'takju',
  u'displayWidth': 720,
  u'sdkInt': 18,
  u'displayHeight': 1184,
  u'naturalOrientation': True
}
```

### Turn on/off screen

```python
d.screen.on()  # Turn on screen
d.screen.off() # Turn off screen
```

Alternative method is:

```python
d.wakeup()    # wakeup the device
d.sleep()     # sleep the device, same as turning off the screen.
```

### Press hard/soft key

```python
d.press.home() # press home key
d.press.back() # press back key
d.press("back")  # the normal way to press back key
d.press(0x07, 0x02)  # press keycode 0x07('0') with META ALT(0x02) on
```

Next keys are currently supported:

- `home`
- `back`
- `left`
- `right`
- `up`
- `down`
- `center`
- `menu`
- `search`
- `enter`
- `delete`(or `del`)
- `recent`(recent apps)
- `volume_up`
- `volume_down`
- `volume_mute`
- `camera`
- `power`

You can find all key code definitions at [Android KeyEvent](http://developer.android.com/reference/android/view/KeyEvent.html).

### Click the screen

```python
d.click(x, y)   # click (x, y) on screen
```

### Swipe

```python
d.swipe(sx, sy, ex, ey)  # swipe from (sx, sy) to (ex, ey)
d.swipe(sx, sy, ex, ey, steps=10)  # swipe from (sx, sy) to (ex, ey) with 10 steps
```

### Drag

```python
d.drag(sx, sy, ex, ey)  # drag from (sx, sy) to (ex, ey)
d.drag(sx, sy, ex, ey, steps=10)  # drag from (sx, sy) to (ex, ey) with 10 steps
```

### Retrieve/Set Orientation

The possible orientation is:
-   `natural` or `n`
-   `left` or `l`
-   `right` or `r`
-   `upsidedown` or `u` (can not be set)

```python
# retrieve orientation, it may be "natural" or "left" or "right" or "upsidedown"
orientation = d.orientation
# set orientation and freeze rotation, notes: "upsidedown" can not be set until Android 4.3.
d.orientation = "l" # or "left"
d.orientation = "r" # or "right"
d.orientation = "n" # or "natural"
```

### Freeze/Un-Freeze rotation

```python
d.freeze_rotation()  # freeze rotation
d.freeze_rotation(False)  # un-freeze rotation
```

### Take screenshot

```python
d.screenshot("home.png")  # take screenshot and save to local file "home.png"
```

### Dump Window Hierarchy

```python
d.dump("hierarchy.xml")  # dump the widown hierarchy and save to local file "hierarchy.xml"
```

### Open notification or quick settings

```python
d.open.notification()   # open notification
d.open.quick_settings() # open quick settings
```

### Wait for idle or window update

```python
d.wait.idle()   # wait for current window to idle
d.wait.update() # wait until window update event occurs
```

### Watcher

You can register [watcher](http://developer.android.com/tools/help/uiautomator/UiWatcher.html) to perform some actions when a selector can not find a match.


#### Register Watcher

When a selector can not find a match, uiautomator will run all registered watchers.

- Click target when conditions match

```python
d.watcher("AUTO_FC_WHEN_ANR").when(text="ANR").when(text="Wait").click(text="Force Close")
# d.watcher(name) ## creates a new named watcher.
#  .when(condition)  ## the UiSelector condition of the watcher.
#  .click(target)  ## perform click action on the target UiSelector.
```

- Press key when conditions match

```python
d.watcher("AUTO_FC_WHEN_ANR").when(text="ANR").when(text="Wait").press.back.home()
# Alternative way to define it as below
d.watcher("AUTO_FC_WHEN_ANR").when(text="ANR").when(text="Wait").press("back", "home")
# d.watcher(name) ## creates a new named watcher.
#  .when(condition)  ## the UiSelector condition of the watcher.
#  .press.<keyname>.<keyname>.....<keyname>.()  ## press keys one by one per the defined sequence.
#  Alternavie way defining key sequence is press(<keybname>, <keyname>, ..., <keyname>)
```

#### Check if the named watcher triggered

A watcher is triggered, which means the watcher was run and all its conditions matched.

```python
d.watcher("watcher_name").triggered  # true in case of the specified watcher triggered, else false
```

#### Remvoe named watcher

```python
d.watcher("watcher_name").remove()  # remove the watcher
```

#### List all watchers

```python
d.watchers  # It's a list of all registered wachers' names
```

#### Check if there is any watcher triggered

```python
d.watchers.triggered  #  true in case of any watcher triggered
```

#### Reset all triggered watchers

```python
d.watchers.reset()  # reset all triggered watchers, after that, d.watchers.triggered will be false.
```

#### Remvoe watchers

```python
d.watchers.remove()  # remove all registered watchers
d.watchers.remove("watcher_name")  # remove the named watcher, same as d.watcher("watcher_name").remove()
```

#### Force to run all watchers

```python
d.watchers.run()  # force to run all registered watchers
```

### Selector

Selector is to identify specific ui object in current window.

```python
d(text='Clock', className='android.widget.TextView')
```

Selector supports next parameters. Please refer to [UiSelector java doc](http://developer.android.com/tools/help/uiautomator/UiSelector.html) for detailed help.

-   `text`
-   `textContains`
-   `textMatches`
-   `textStartsWith`
-   `className`
-   `classNameMatches`
-   `description`
-   `descriptionContains`
-   `descriptionMatches`
-   `descriptionStartsWith`
-   `checkable`
-   `checked`
-   `clickable`
-   `longClickable`
-   `scrollable`
-   `enabled`
-   `focusable`
-   `focused`
-   `selected`
-   `packageName`
-   `packageNameMatches`
-   `resourceId`
-   `resourceIdMatches`
-   `index`
-   `instance`
-   `fromParent`
-   `childSelector`

#### Check if the specific ui object exists

```python
d(text="Settings").exists # True if exists, else False
d.exists(text="Settings") # alias of above property.
```

#### Retrieve the info of the specific ui object

```python
d(text="Settings").info
```

Below is a possible result:

```
{ u'contentDescription': u'',
  u'checked': False,
  u'scrollable': False,
  u'text': u'Settings',
  u'packageName': u'com.android.launcher',
  u'selected': False,
  u'enabled': True,
  u'bounds': {u'top': 385,
              u'right': 360,
              u'bottom': 585,
              u'left': 200},
  u'className': u'android.widget.TextView',
  u'focused': False,
  u'focusable': True,
  u'clickable': True,
  u'chileCount': 0,
  u'longClickable': True,
  u'visibleBounds': {u'top': 385,
                     u'right': 360,
                     u'bottom': 585,
                     u'left': 200},
  u'checkable': False
}
```

#### Perform click on the specific ui object

```python
d(text="Settings").click()  # click on the center of the specific ui object
d(text="Settings").click.bottomright()  # click on the bottomright corner of the specific ui object
d(text="Settings").click.topleft()  # click on the topleft corner of the specific ui object
d(text="Settings").click.wait()  # click and wait until the new window update
```

#### Perform long click on the specific ui object

```python
d(text="Settings").long_click()  # long click on the center of the specific ui object
d(text="Settings").long_click.bottomright()  # long click on the bottomright corner of the specific ui object
d(text="Settings").long_click.topleft()  # long click on the topleft corner of the specific ui object
```

#### Set/Clear text of editable field

```python
d(text="Settings").clear_text()  # clear the text
d(text="Settings").set_text("My text...")  # set the text
```

#### Drag the ui object to another point or ui object

```python
d(text="Settings").drag.to(x, y, steps=100)  # drag the ui object to point (x, y)
d(text="Settings").drag.to(text="Clock", steps=50)  # drag the ui object to another ui object(center)
```

#### Swipe from the center of the ui object to its edge

Swipe supports 4 directions:

-   `left`
-   `right`
-   `top`
-   `bottom`

```python
d(text="Settings").swipe.right()
d(text="Settings").swipe.left(steps=10)
d(text="Settings").swipe.up(steps=10)
d(text="Settings").swipe.down()
```

#### Two point gesture from one point to another

```python
from uiautomator import point

d(text="Settings").gesture(point(sx1, sy1), point(sx2, sy2)).to(point(ex1, ey1), point(ex2, ey2))
```

#### Two point gesture on the specific ui object

Supports two gestures:
- `In`, from edge to center
- `Out`, from center to edge

```python
d(text="Settings").pinch.In(percent=100, steps=10)  # from edge to center. here is "In" not "in"
d(text="Settings").pinch.Out()  # from center to edge
```

#### Perform fling on the specific ui object(scrollable)

Possible properties:
- `horiz` or `vert`
- `forward` or `backward` or `toBeginning` or `toEnd`

```python
d(scrollable=True).fling()  # fling forward(default) vertically(default) 
d(scrollable=True).fling.horiz.forward()  # fling forward horizentally
d(scrollable=True).fling.vert.backward()  # fling backward vertically
d(scrollable=True).fling.horiz.toBeginning(max_swipes=1000)  # fling to beginning horizentally
d(scrollable=True).fling.toEnd()  # fling to end vertically
```

#### Perform scroll on the specific ui object(scrollable)

Possible properties:
- `horiz` or `vert`
- `forward` or `backward` or `toBeginning` or `toEnd`, or `to`

```python
d(scrollable=True).scroll(stpes=10)  # scroll forward(default) vertically(default)
d(scrollable=True).scroll.horiz.forward(steps=100)  # scroll forward horizentally
d(scrollable=True).scroll.vert.backward()  # scroll backward vertically
d(scrollable=True).scroll.horiz.toBeginning(steps=100, max_swipes=1000)  # scroll to beginning horizentally
d(scrollable=True).scroll.toEnd()  # scroll to end vertically
d(scrollable=True).scroll.to(text="Security")  # scroll forward vertically until specific ui object appears
```

#### Wait until the specific ui object appears or gone

```python
d(text="Settings").wait.exists(timeout=3000)  # wait until the ui object appears
d(text="Settings").wait.gone(timeout=1000)  # wait until the ui object gone
```

---

## Issues

Please submit ticket on [github issues](https://github.com/xiaocong/uiautomator/issues) in case of any issue.

## Notes

- Android [uiautomator][] works on Android 4.1+, so before using it, make sure your device is Android4.1+.
- Some methods are only working on Android 4.2/4.3, so you'd better read detailed [java documentation of uiautomator](http://developer.android.com/tools/help/uiautomator/index.html) before using it.
- The module uses [uiautomator-jsonrpc-server](https://github.com/xiaocong/android-uiautomator-jsonrpcserver) as its daemon to communicate with devices.


[uiautomator]: http://developer.android.com/tools/testing/testing_ui.html "Android ui testing"
