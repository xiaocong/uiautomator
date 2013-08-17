#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uiautomator

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


requires = ["jsonrpclib"]

setup(name='uiautomator',
      version=uiautomator.__version__,
      description='Python Wrapper for Android UiAutomator test tool',
      long_description=uiautomator.__doc__,
      author=uiautomator.__author__,
      author_email='xiaocong@gmail.com',
      url='',
      install_requires=requires,
      py_modules=['uiautomator'],
      scripts=['uiautomator.py'],
      license='MIT',
      platforms = 'any',
      classifiers=(
      	'Development Status :: 2 - Development',
      	'Environment :: Console',
      	'Intended Audience :: Developers',
      	'Operating System :: POSIX',
      	'Programming Language :: Python',
      	'Topic :: Software Development :: Testing',
      )
)
