#!/bin/sh -ex

#
# Package installation.
#

apt-get -y install nginx
ln -sf /usr/local/tiledrawer/nginx/setup-time.conf /etc/nginx/sites-enabled/default
/etc/init.d/nginx restart

apt-get -y install unzip gunicorn memcached \
                   python-pip python-imaging python-gevent python-memcache \
                   osm2pgsql postgis python-mapnik \

ln -s /usr/lib/postgresql/9.1/bin/shp2pgsql /usr/bin/shp2pgsql # really?
pip install TileStache ModestMaps Cascadenik

mv /etc/memcached.conf /etc/memcached-orig.conf
ln -s /usr/local/tiledrawer/memcached/memcached.conf /etc/memcached.conf
/etc/init.d/memcached restart

#
# Prepare sysctl settings and a better-tuned Postgresql, based on
# Frederik Ramm's 2010 "Optimizing" SOTM talk:
# http://www.geofabrik.de/media/2010-07-10-rendering-toolchain-performance.pdf
#

/usr/local/tiledrawer/ubuntu/sysctl.sh
mv /etc/sysctl.conf /etc/sysctl-orig.conf
ln -s /usr/local/tiledrawer/ubuntu/etc/sysctl.conf /etc/sysctl.conf

mv /etc/postgresql/9.1/main/postgresql.conf /etc/postgresql/9.1/main/postgresql-orig.conf
mv /etc/postgresql/9.1/main/pg_hba.conf /etc/postgresql/9.1/main/pg_hba-orig.conf
ln -s /usr/local/tiledrawer/postgres/9.1/postgresql.conf /etc/postgresql/9.1/main/postgresql.conf
ln -s /usr/local/tiledrawer/postgres/9.1/pg_hba.conf /etc/postgresql/9.1/main/pg_hba.conf
/etc/init.d/postgresql restart

#
# Build ourselves a usable OSM planet database.
#

sudo -u postgres createuser -DRS osm
sudo -u postgres createdb -O osm planet_osm

psql -U postgres planet_osm < /usr/share/postgresql/9.1/contrib/postgis-1.5/postgis.sql
psql -U postgres planet_osm < /usr/share/postgresql/9.1/contrib/postgis-1.5/spatial_ref_sys.sql

echo 'ALTER TABLE geometry_columns OWNER TO osm;' | psql -U postgres planet_osm
echo 'ALTER TABLE spatial_ref_sys OWNER TO osm;' | psql -U postgres planet_osm
