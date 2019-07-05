#!/usr/bin/env python
# -*- coding: utf-8 -*-
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


requires = [
    "urllib3>=1.7.1",
    'selenium>=3.1',
    'pillow'
]
test_requires = [
    'nose>=1.0',
    'mock>=1.0.1',
    'coverage>=3.6',
]

version = '0.3.8.7'

setup(
    name='atc_uiautomator',
    version=version,
    description='Python Wrapper for Android UiAutomator test_set tool',
    long_description='Python wrapper for Android uiautomator tool.',
    author='Xiaocong He',
    author_email='xiaocong@gmail.com,hongbin.bao@gmail.com',
    url='https://github.com/xiaocong/uiautomator',
    download_url='https://github.com/xiaocong/uiautomator/tarball/%s' % version,
    keywords=[
        'testing', 'android', 'uiautomator'
    ],
    install_requires=requires,
    tests_require=test_requires,
    test_suite="nose.collector",
    packages=['uiautomator'],
    package_data={
        'uiautomator': [
            'uiautomator/libs/bundle.jar',
            'uiautomator/libs/uiautomator-stub.jar',
            'uiautomator/libs/app-uiautomator-test_set.apk',
            'uiautomator/libs/app-uiautomator.apk'
        ]
    },
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
        'Programming Language :: Python :: 3.4',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Testing'
    )
)
