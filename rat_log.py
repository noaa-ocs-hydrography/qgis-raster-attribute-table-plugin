# coding=utf-8
""""RAT logger

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2021-04-30'
__copyright__ = 'Copyright 2021, ItOpen'

from qgis.core import QgsMessageLog, Qgis

def rat_log(message, level=Qgis.Info):

    QgsMessageLog.logMessage(message, "RAT", level)
