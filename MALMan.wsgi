#!/usr/bin/python2
import sys
from os import path

activate_this = path.join(path.dirname(path.abspath( __file__ )))
execfile(activate_this, dict(__file__=activate_this))

sys.path.insert(0, path.dirname(path.abspath( __file__ )))

from MALMan import app as application

