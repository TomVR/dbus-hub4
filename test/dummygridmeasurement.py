#!/usr/bin/env python

# The dummy measurement at the grid. At the dbus it represents itself as qwacs pvinverter
# because I (mis-)use a qwacs wireless ac sensor to measure what is happening at the grid
# connection point of my house. dbus-qwacs needs to have another option, Grid L1,2,3 to
# make this a bit better understandable.

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
                type=str, default="com.victronenergy.pvinverter.qwacs_di0")

args = parser.parse_args()

# Init logging
logging.basicConfig(level=logging.DEBUG)
logging.info(__file__ + " is starting up, use -h argument to see optional arguments")

# Have a mainloop, so we can send/receive asynchronous calls to and from dbus
DBusGMainLoop(set_as_default=True)

pvac_output = DbusDummyService(
    servicename=args.name,
    deviceinstance=2,
    paths={
        '/Ac/L1/Power': {'initial': -100, 'update': 10},
        '/Ac/L1/Current': {'initial': -10, 'update': 1}
    })

print 'Connected to dbus, and switching over to gobject.MainLoop() (= event based)'
mainloop = gobject.MainLoop()
mainloop.run()




