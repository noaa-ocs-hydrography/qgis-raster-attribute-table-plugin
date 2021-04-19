# coding=utf-8
""""RAT raster classification

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2021-04-19'
__copyright__ = 'Copyright 2021, ItOpen'

from qgis.core import (
    QgsPalettedRasterRenderer,
)

def rat_classify(raster_layer, band, column):
    classes = []
    # create classes
    klass = QgsPalettedRasterRenderer.Class(value, color, label)
    classes.append(klass)

    renderer = QgsPalettedRasterRenderer(raster_layer, band, classes)
    raster_layer.setRenderer(renderer)
