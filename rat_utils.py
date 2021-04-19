# coding=utf-8
""""RAT Utilities

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2021-04-19'
__copyright__ = 'Copyright 2021, ItOpen'

from osgeo import gdal

def get_rat(raster_layer, band):

    headers = []
    values = {}

    ds = gdal.OpenEx(raster_layer.source())
    if ds:
        band = ds.GetRasterBand(band)
        if band:
            rat = band.GetDefaultRAT()
            for i in range(0, rat.GetColumnCount()):
                column = rat.GetNameOfCol(i)
                headers.append(column)
                values[column] = []

            for r in range(0, rat.GetRowCount()):
                for c in range(0, rat.GetColumnCount()):
                    values[headers[c]].append(rat.GetValueAsString(r, c))

    # Search for sidecar DBF files
    if not values:
        pass

    return values
