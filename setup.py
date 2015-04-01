#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uiautomator
import multiprocessing

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


requires = [
    "urllib3>=1.7.1"
]
test_requires = [
    'nose>=1.0',
    'mock>=1.0.1',
    'coverage>=3.6'
]

setup(
    name='uiautomator',
    version=uiautomator.__version__,
    description='Python Wrapper for Android UiAutomator test tool',
    long_description=uiautomator.__doc__,
    author=uiautomator.__author__,
    author_email='xiaocong@gmail.com',
    url='https://github.com/xiaocong/uiautomator',
    install_requires=requires,
    tests_require=test_requires,
    test_suite="nose.collector",
    packages=['uiautomator'],
    package_data={'uiautomator': ['uiautomator/libs/bundle.jar', 'uiautomator/libs/uiautomator-stub.jar']},
    include_package_data=True,
    license='MIT',
    platforms='any',
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Testing'
    )
)
