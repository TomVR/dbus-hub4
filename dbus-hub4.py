#!/usr/bin/env python
# -*- coding: utf-8 -*-

# hub4. status of code is first initial draft
# function: subscribes to power measured at meter of the house (in this case measured with a 
# wireless AC current sensor), and sends that measurement at one second intervals to the multi

import dbus
import pprint
import platform
import os
import gobject
import sys
import argparse
import logging
from dbus.mainloop.glib import DBusGMainLoop

softwareversion = '0.0'

# our own packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), './ext/velib_python'))
from vedbus import VeDbusItemImport

DBusGMainLoop(set_as_default=True)

# Connect to the sessionbus. Note that on ccgx we use systembus instead.
dbusConn = dbus.SystemBus() if (platform.machine() == 'armv7l') else dbus.SessionBus()

# dictionary containing the different items
objects = {}

# check if the vbus.ttyO1 exists (it normally does on a ccgx, and for linux a pc, there is
# some emulator.
# hasVEBus = 'com.victronenergy.vebus.ttyO1' in dbusConn.list_names()

def forward():
	v = dbus.Double(-1 * objects['grid'].get_value(), variant_level=1)
	objects['target'].set_value(v)
	logging.debug('writing %s' % v)
	return True # keep timer running

def main():
	# Argument parsing
	parser = argparse.ArgumentParser(
		description='dbus-hub4 v%s: communication to VRM Portal database' % softwareversion
	)

	parser.add_argument("-d", "--debug", help="set logging level to debug",
					action="store_true")

	args = parser.parse_args()

	# Init logging
	logging.basicConfig(level=(logging.DEBUG if args.debug else logging.INFO))
	logging.info("%s v%s is starting up" % (__file__, softwareversion))
	logLevel = {0: 'NOTSET', 10: 'DEBUG', 20: 'INFO', 30: 'WARNING', 40: 'ERROR'}
	logging.info('Loglevel set to ' + logLevel[logging.getLogger().getEffectiveLevel()])

	# Application starts here
	objects['grid'] = VeDbusItemImport(
		dbusConn, 'com.victronenergy.pvinverter.qwacs_di2', '/Ac/L1/Power')

	objects['target'] = VeDbusItemImport(
		dbusConn, 'com.victronenergy.vebus.ttyO1', '/Hub4/ExternalAcCurrentMeasurement')

	gobject.timeout_add(1000, forward)

	print 'Connected to dbus, and switching over to gobject.MainLoop() (= event based)'
	mainloop = gobject.MainLoop()
	mainloop.run()

if __name__ == "__main__":
	main()
