#!/usr/bin/env python

from dbus.mainloop.glib import DBusGMainLoop
import gobject
import argparse
import logging
import sys
import os

# our own packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../ext/velib_python'))
from dbusdummyservice import DbusDummyService

# Argument parsing
parser = argparse.ArgumentParser(
    description='dummy dbus service'
)

parser.add_argument("-n", "--name", help="the D-Bus service you want me to claim",
                type=str, default="com.victronenergy.vebus.ttyO1")

args = parser.parse_args()

# Init logging
logging.basicConfig(level=logging.DEBUG)
logging.info(__file__ + " is starting up, use -h argument to see optional arguments")

# Have a mainloop, so we can send/receive asynchronous calls to and from dbus
DBusGMainLoop(set_as_default=True)


# 'Hub4/ExternalAcCurrentMeasurement': 0.0,
# 'Hub4/ExternalAcCurrentSetpoint': 0.0,
# 'Hub4/IAction': 300,
# 'Hub4/PAction': [],


pvac_output = DbusDummyService(
    servicename=args.name,
    deviceinstance=0,
    paths={
        '/Hub4/ExternalAcCurrentMeasurement': {'initial': 0}
    })

print 'Connected to dbus, and switching over to gobject.MainLoop() (= event based)'
mainloop = gobject.MainLoop()
mainloop.run()




