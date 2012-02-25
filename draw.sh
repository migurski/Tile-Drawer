#!/bin/sh -x

#
# Provide Tilestache a spacious directory to cache tiles.
#

if [ -d /mnt ]; then
    mkdir /mnt/cache
    ln -s /mnt/cache /var/cache/tilestache
    chmod a+rwxt /mnt/cache
else
    mkdir /tmp/cache
    ln -s /tmp/cache /var/cache/tilestache
    chmod a+rwxt /tmp/cache
fi

#
# Start TileStache under gunicorn, and switch nginx configuration to tile proxy.
#

ln -s /usr/local/tiledrawer/gunicorn/init.d/tilestache-gunicorn.sh /etc/init.d/tilestache-gunicorn.sh
/etc/init.d/tilestache-gunicorn.sh start

ln -sf /usr/local/tiledrawer/nginx/drawer-time.conf /etc/nginx/sites-enabled/default
/etc/init.d/nginx restart

#
# Dump out rendering tables to shapefiles while Tilestache and nginx are on their way.
#

pgsql2shp -rk -f /tmp/tile-drawer.coastline.shp -u osm planet_osm coastline
pgsql2shp -rk -f /tmp/tile-drawer.osm2pgsql-line.shp -u osm planet_osm planet_osm_line
pgsql2shp -rk -f /tmp/tile-drawer.osm2pgsql-point.shp -u osm planet_osm planet_osm_point
pgsql2shp -rk -f /tmp/tile-drawer.osm2pgsql-polygon.shp -u osm planet_osm planet_osm_polygon

pgsql2shp -rk -f /tmp/tile-drawer.imposm-admin.shp -u osm planet_osm imposm_admin
pgsql2shp -rk -f /tmp/tile-drawer.imposm-aeroways.shp -u osm planet_osm imposm_aeroways
pgsql2shp -rk -f /tmp/tile-drawer.imposm-amenities.shp -u osm planet_osm imposm_amenities
pgsql2shp -rk -f /tmp/tile-drawer.imposm-buildings.shp -u osm planet_osm imposm_buildings

pgsql2shp -rk -f /tmp/tile-drawer.imposm-landusages.shp -u osm planet_osm imposm_landusages
pgsql2shp -rk -f /tmp/tile-drawer.imposm-mainroads.shp -u osm planet_osm imposm_mainroads
pgsql2shp -rk -f /tmp/tile-drawer.imposm-minorroads.shp -u osm planet_osm imposm_minorroads
pgsql2shp -rk -f /tmp/tile-drawer.imposm-motorways.shp -u osm planet_osm imposm_motorways

pgsql2shp -rk -f /tmp/tile-drawer.imposm-places.shp -u osm planet_osm imposm_places
pgsql2shp -rk -f /tmp/tile-drawer.imposm-railways.shp -u osm planet_osm imposm_railways
pgsql2shp -rk -f /tmp/tile-drawer.imposm-waterareas.shp -u osm planet_osm imposm_waterareas
pgsql2shp -rk -f /tmp/tile-drawer.imposm-waterways.shp -u osm planet_osm imposm_waterways

pgsql2shp -rk -f /tmp/tile-drawer.imposm-landusages-gen0.shp -u osm planet_osm imposm_landusages_gen0
pgsql2shp -rk -f /tmp/tile-drawer.imposm-landusages-gen1.shp -u osm planet_osm imposm_landusages_gen1
pgsql2shp -rk -f /tmp/tile-drawer.imposm-mainroads-gen0.shp -u osm planet_osm imposm_mainroads_gen0
pgsql2shp -rk -f /tmp/tile-drawer.imposm-mainroads-gen1.shp -u osm planet_osm imposm_mainroads_gen1

pgsql2shp -rk -f /tmp/tile-drawer.imposm-motorways-gen0.shp -u osm planet_osm imposm_motorways_gen0
pgsql2shp -rk -f /tmp/tile-drawer.imposm-motorways-gen1.shp -u osm planet_osm imposm_motorways_gen1
pgsql2shp -rk -f /tmp/tile-drawer.imposm-railways-gen0.shp -u osm planet_osm imposm_railways_gen0
pgsql2shp -rk -f /tmp/tile-drawer.imposm-railways-gen1.shp -u osm planet_osm imposm_railways_gen1

pgsql2shp -rk -f /tmp/tile-drawer.imposm-roads.shp -u osm planet_osm imposm_roads
pgsql2shp -rk -f /tmp/tile-drawer.imposm-roads-gen0.shp -u osm planet_osm imposm_roads_gen0
pgsql2shp -rk -f /tmp/tile-drawer.imposm-roads-gen1.shp -u osm planet_osm imposm_roads_gen1

pgsql2shp -rk -f /tmp/tile-drawer.imposm-transport-areas.shp -u osm planet_osm imposm_transport_areas
pgsql2shp -rk -f /tmp/tile-drawer.imposm-transport-points.shp -u osm planet_osm imposm_transport_points
pgsql2shp -rk -f /tmp/tile-drawer.imposm-waterareas-gen0.shp -u osm planet_osm imposm_waterareas_gen0
pgsql2shp -rk -f /tmp/tile-drawer.imposm-waterareas-gen1.shp -u osm planet_osm imposm_waterareas_gen1

#
# Zip up shapefiles for possible future use in Tilemill, etc.
#

zip -j /usr/local/tiledrawer/progress/osm-shapefiles.zip /tmp/tile-drawer.*-*.??? /tmp/tile-drawer.coastline.???
zip -j /usr/local/tiledrawer/progress/osm-shapefiles-osm2pgsql.zip /tmp/tile-drawer.osm2pgsql-*.??? /tmp/tile-drawer.coastline.???
zip -j /usr/local/tiledrawer/progress/osm-shapefiles-imposm.zip /tmp/tile-drawer.imposm-*.??? /tmp/tile-drawer.coastline.???

rm /tmp/tile-drawer.*-*.??? /tmp/tile-drawer.coastline.???
