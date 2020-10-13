# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name			 	 : RAT
Description          : RAT plugin
Date                 : 11/Oct/2010
copyright            : (C) 2020 by ItOpen
email                : info@itopen.it
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


def classFactory(iface):
    # load GeoCoding class from file GeoCoding
    from .RasterAttributeTable import RasterAttributeTable
    return RasterAttributeTable(iface)
