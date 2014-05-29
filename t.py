from uiautomator import device as d

def my_call_back(device=None):
  print 'callback....'
  return True  # True means not to call next callbacks

d.handlers.on(my_call_back)
d(text='Not Found').click()
