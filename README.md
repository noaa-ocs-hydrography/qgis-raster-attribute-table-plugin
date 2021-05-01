
![test_workflow](https://github.com/elpaso/qgis-raster-attribute-table-plugin/actions/workflows/python-app.yml/badge.svg)

# Raster Attribute Table QGIS Plugin

QGIS plugin to display and edit Raster Attribute Tables (RATs) for discrete rasters using
paletted/unique-values renderer.

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

+ Color support (RGBA)

## Current limitations/unsupported features

+ Linear binning
+ Range values

## Testing

```
pytest --forked -s
```
