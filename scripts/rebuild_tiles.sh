#!/bin/bash
set -e

INPUT=$1

echo "Converting GeoJSON → OSM"

ogr2osm $INPUT -o /tmp/data.osm

echo "OSM → PBF"

osmium cat /tmp/data.osm -o /tmp/data.pbf

echo "Building Valhalla tiles"

valhalla_build_tiles -c /data/valhalla/valhalla.json /tmp/data.pbf

echo "Tiles rebuilt"