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
from dbusmonitor import DbusMonitor

DBusGMainLoop(set_as_default=True)

# Connect to the sessionbus. Note that on ccgx we use systembus instead.
dbusConn = dbus.SystemBus() if (platform.machine() == 'armv7l') else dbus.SessionBus()

dbusmonitor = None
target = None

# Called on  1 second interval, takes values from qwacs AC sensor and feeds it to VE.Bus
def forward():

	# Get power, and use it to get the direction of the current (exporting or buying)
	# To get this as the Victron standard (negative = exporting to grid, positive is taking
	# power from grid), invert the sign. Or just rewire the qwacs sensor :).
	grid_power = dbusmonitor.get_value('com.victronenergy.pvinverter.qwacs_di0', '/Ac/L1/Power')
	grid_current = dbusmonitor.get_value('com.victronenergy.pvinverter.qwacs_di0', '/Ac/L1/Current')

	if grid_power is None or grid_current is None:
		logging.error("No grid measurement? grid_power=%s, grid_current=%s" % (grid_power, grid_current))
		logging.error("Exiting...")
		sys.exit(1)

	s = -1 if grid_power < 0 else 1
	grid_text = 'selling' if grid_power < 0 else 'buying '
	signed_current = dbus.Double(s * grid_current, variant_level=1)

	vebus_current = dbusmonitor.get_value('com.victronenergy.vebus.ttyO1', '/Ac/ActiveIn/L1/I')
	vebus_power = dbusmonitor.get_value('com.victronenergy.vebus.ttyO1', '/Ac/ActiveIn/L1/P')
	vebus_text = 'charging' if vebus_power > 0 else 'discharging'
	vebus_bat_voltage = dbusmonitor.get_value('com.victronenergy.vebus.ttyO1', '/Dc/V')

	try:
		logging.debug("Grid: %4.0f W  %5.2f A AC (%s).   Storage: %4.0f W  %5.2f A AC (%.1f VDC, %s)" %
			(grid_power, grid_current, grid_text, vebus_power, vebus_current, vebus_bat_voltage, vebus_text))
		target.set_value(signed_current)
	except:
		import traceback
		traceback.print_exc()
		sys.exit(1)

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
	dummy = {'code': None, 'whenToLog': 'configChange', 'accessLevel': None}
	global dbusmonitor
	dbusmonitor = DbusMonitor({
		'com.victronenergy.pvinverter': {
			'/Ac/L1/Current': dummy,
			'/Ac/L1/Power': dummy},  # since current is unsigned, use power to get the sign
		'com.victronenergy.vebus': {
			'/Ac/ActiveIn/L1/I': dummy,
			'/Ac/ActiveIn/L1/P': dummy,
			'/Dc/V': dummy,
			'/Dc/I': dummy}
	})

	# Connect to the multi inverter/charger
	# target is the parameter to which we´ll write the measurement at the grid.
	global target
	target = VeDbusItemImport(
		dbusConn, 'com.victronenergy.vebus.ttyO1', '/Hub4/ExternalAcCurrentMeasurement')

	# Set default IAction and PAction
	# To play around, it is possible to send other values while this script is running. Just
	# don't forget that they'll be reset once this script restarts.
	VeDbusItemImport(dbusConn, 'com.victronenergy.vebus.ttyO1', '/Hub4/PAction').set_value(
		dbus.Int32(args.paction, variant_level=1))
	VeDbusItemImport(dbusConn, 'com.victronenergy.vebus.ttyO1', '/Hub4/IAction').set_value(
		dbus.Int32(args.iaction, variant_level=1))

	# Initiate timer on fixed interval
	gobject.timeout_add(1000, forward)

	print 'Connected to dbus, and switching over to gobject.MainLoop() (= event based)'
	mainloop = gobject.MainLoop()
	mainloop.run()

if __name__ == "__main__":
	main()
