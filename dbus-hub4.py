#!/usr/bin/env python
# -*- coding: utf-8 -*-

# hub4. status of code is first initial draft
# function: subscribes to power measured at meter of the house (in this case measured with a 
# wireless AC current sensor), and sends that measurement at one second intervals to the multi

# Set Paction to 1 and Iaction to 500 to get a slow working, slightly overshooting, but at least
# stable, regulation. With a bit more tweeking of P and I it will probably work even better.
# dbus -y com.victronenergy.vebus.ttyO1 /Hub4/PAction SetValue 1
# dbus -y com.victronenergy.vebus.ttyO1 /Hub4/IAction SetValue 500

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

# Called on  1 second interval, takes values from qwacs AC sensor and feeds it to VE.Bus
def forward():

	# Get power, and use it to get the direction of the current (exporting or buying)
	# To get this as the Victron standard (negative = exporting to grid, positive is taking
	# power from grid), invert the sign. Or just rewire the qwacs sensor :).
	grid_power = 1 * objects['grid_power'].get_value()

	grid_current = objects['grid_current'].get_value()

	s = -1 if grid_power < 0 else 1
	grid_text = 'selling' if grid_power < 0 else 'buying'
	signed_current = dbus.Double(s * grid_current, variant_level=1)

	vebus_current = objects['vebus_current'].get_value()
	vebus_power = objects['vebus_power'].get_value()
	vebus_text = 'charging' if vebus_power > 0 else 'discharging'

	try:
		print ("Grid: %4.0f W  %5.2f A AC (%s).   Storage: %4.0f W  %5.2f A AC (%s, %.1f VDC)" %
			(grid_power, grid_current, grid_text,
			vebus_power, vebus_current, vebus_text, objects['battery_voltage'].get_value()))
		objects['target'].set_value(signed_current)
	except:
		import traceback
		traceback.print_exc()
		sys.exit()

	return True # keep timer running


def main():
	# Argument parsing
	parser = argparse.ArgumentParser(
		description='dbus-hub4 v%s: communication to VRM Portal database' % softwareversion
	)
	parser.add_argument(
		"-d", "--debug", help="set logging level to debug",	action="store_true")
	parser.add_argument(
		"-p", "--paction", help="PID loop p-action, default=1", type=int, default="1")
	parser.add_argument(
		"-i", "--iaction", help="PID loop i-action, default=500", type=int, default="500")
	args = parser.parse_args()

	# Init logging
	logging.basicConfig(level=(logging.DEBUG if args.debug else logging.INFO))
	logging.info("%s v%s is starting up" % (__file__, softwareversion))
	logLevel = {0: 'NOTSET', 10: 'DEBUG', 20: 'INFO', 30: 'WARNING', 40: 'ERROR'}
	logging.info('Loglevel set to ' + logLevel[logging.getLogger().getEffectiveLevel()])

	# ========= Application starts here ===========

	# Connect to the grid measurement.
	acindbusname = 'com.victronenergy.pvinverter.qwacs_di0'
	objects['grid_current'] = VeDbusItemImport(
		dbusConn, acindbusname, '/Ac/L1/Current')
	# We use the current to feed in the pid loop, but since the current is unsigned (why, perhaps fix this
	# in qwacs to make it conform the rest?) we take power as well, which is signed, and use its sign.
	objects['grid_power'] = VeDbusItemImport(
		dbusConn, acindbusname, '/Ac/L1/Power')

	# Connect to the multi inverter/charger
	# target is the parameter to which we´ll write the measurement at the grid.
	objects['target'] = VeDbusItemImport(
		dbusConn, 'com.victronenergy.vebus.ttyO1', '/Hub4/ExternalAcCurrentMeasurement')

	# Set default IAction and PAction
	# To play around, it is possible to send other values while this script is running. Just
	# don't forget that they'll be reset once this script restarts.
	VeDbusItemImport(dbusConn, 'com.victronenergy.vebus.ttyO1', '/Hub4/PAction').set_value(
		dbus.Int32(args.paction, variant_level=1))
	VeDbusItemImport(dbusConn, 'com.victronenergy.vebus.ttyO1', '/Hub4/IAction').set_value(
		dbus.Int32(args.iaction, variant_level=1))

	# Connect to vebus current & power, just for showing data on the commandline
	objects['vebus_current'] = VeDbusItemImport(
		dbusConn, 'com.victronenergy.vebus.ttyO1', '/Ac/ActiveIn/L1/I')
	objects['vebus_power'] = VeDbusItemImport(
		dbusConn, 'com.victronenergy.vebus.ttyO1', '/Ac/ActiveIn/L1/P')
	objects['battery_voltage'] = VeDbusItemImport(
		dbusConn, 'com.victronenergy.vebus.ttyO1', '/Dc/V')

	# Initiate timer on fixed interval
	gobject.timeout_add(1000, forward)

	print 'Connected to dbus, and switching over to gobject.MainLoop() (= event based)'
	mainloop = gobject.MainLoop()
	mainloop.run()

if __name__ == "__main__":
	main()
