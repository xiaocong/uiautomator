#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import logging
import mock
import os
import subprocess
import uiautomator
import multiprocessing


def _create_next_local_port_stub(ports):
  def _next_local_port_stub(_):
    max_used_port = max(x[1] for x in ports) if ports else 0
    return max(max_used_port, uiautomator.LOCAL_PORT) + 1
  return _next_local_port_stub


def _create_adb_forward_stub(serial, ports):
  def _adb_forward_stub(local_port, device_port, rebind=True):
    ports.append([serial, local_port, device_port])
  return _adb_forward_stub


def _create_adb_forward_list_stub(ports):
  def _adb_forward_list_stub():
    return [[x[0], "tcp:" + str(x[1]), "tcp:" + str(x[2])] for x in ports]
  return _adb_forward_list_stub


class TestMultiProcess(unittest.TestCase):

  def setUp(self):
    self.ports = []

  def create_device(self, serial):
      device = uiautomator.Device(serial=serial)
      device.server.adb = mock.MagicMock()
      device.server.adb.device_serial = lambda: serial
      device.server.adb.forward = _create_adb_forward_stub(serial, self.ports)
      device.server.adb.forward_list = _create_adb_forward_list_stub(self.ports)
      device.server.ping = mock.MagicMock(return_value="pong")
      return device

  def test_run_sequential(self):
      uiautomator.next_local_port = _create_next_local_port_stub(self.ports)

      device1 = self.create_device("1")
      device1.server.start()

      device2 = self.create_device("2")
      device2.server.start()

      self.assertNotEqual(device1.server.local_port, device2.server.local_port)

  def test_run_interleaving(self):
      uiautomator.next_local_port = _create_next_local_port_stub(self.ports)

      device1 = self.create_device("1")
      device2 = self.create_device("2")

      device1.server.start()
      device2.server.start()

      self.assertNotEqual(device1.server.local_port, device2.server.local_port)
