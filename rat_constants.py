# coding=utf-8
""""Constants for RAT plugin

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2021-04-21'
__copyright__ = 'Copyright 2021, ItOpen'

from osgeo import gdal

RAT_COLOR_HEADER_NAME = 'RAT Color'
RAT_CUSTOM_PROPERTY_CLASSIFICATION_CRITERIA = 'RasterAttributeTable-Criteria'

# These fields must be unique in a RAT
RAT_UNIQUE_FIELDS = (
    gdal.GFU_Min,
    gdal.GFU_Max,
    gdal.GFU_MinMax,
    gdal.GFU_Red,
    gdal.GFU_Green,
    gdal.GFU_Blue,
    gdal.GFU_Alpha,
    gdal.GFU_RedMin,
    gdal.GFU_GreenMin,
    gdal.GFU_BlueMin,
    gdal.GFU_AlphaMin,
    gdal.GFU_RedMax,
    gdal.GFU_GreenMax,
    gdal.GFU_BlueMax,
    gdal.GFU_AlphaMax
)
