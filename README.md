---
marp: false
---

# Raster Attribute Table QGIS Plugin

QGIS plugin to display and edit Raster Attribute Tables (RATs) for discrete rasters.

## Supported formats

+ GDAL `.aux.xml` format
+ Sidecar `.vat.dbf` format

## Supported features

+ RAT creation from a paletted/unique values styled layer
+ QGIS style classification on arbitrary RAT columns
+ RAT editing:

  - values editing
  - row add/remove
  - column add/remove

+ RAT export to `vat.dbf` format
+ Color support (RGBA)

## Current limitations/unsupported features

+ Linear binning
+ Range values

## Testing

```
pytest --forked -s
```
