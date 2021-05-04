
![test_workflow](https://github.com/elpaso/qgis-raster-attribute-table-plugin/actions/workflows/python-app.yml/badge.svg)

# Raster Attribute Table QGIS Plugin

QGIS plugin to display and edit Raster Attribute Tables (RATs) for discrete rasters using
paletted/unique-values renderer.

The plugin offers also limited support for continuous raster RATs using the single-band/presudocolor renderer.

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

## Demo

### RAT creation and editing

https://user-images.githubusercontent.com/142164/117006900-47639c80-ace9-11eb-97b9-bf74aa30ece8.mp4

### Existing RAT classification

https://user-images.githubusercontent.com/142164/117006916-4af72380-ace9-11eb-96f2-aa8d15b19b9f.mp4


## Current limitations/unsupported features

+ Linear binning

## Testing

```
pytest --forked -s
```
