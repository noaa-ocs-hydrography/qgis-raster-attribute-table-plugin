# coding=utf-8
""""RAT plugin

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2021-04-29'
__copyright__ = 'Copyright 2021, ItOpen'


def classFactory(iface):
    # load GeoCoding class from file GeoCoding
    from .RasterAttributeTable import RasterAttributeTable
    return RasterAttributeTable(iface)
