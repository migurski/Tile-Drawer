#!/bin/sh -ex

#
# It's assumed that /usr/local/tiledrawer already exists.
#

if [ -d /mnt ]; then
    ln -s /mnt /usr/local/tiledrawer/progress
else
    ln -s /tmp /usr/local/tiledrawer/progress
fi

ln -s /var/log/tiledrawer.log /usr/local/tiledrawer/progress/tiledrawer.log

#
# Package installation.
#

apt-get -y install nginx

# use an nginx config specifically for the setup process
ln -sf /usr/local/tiledrawer/nginx/setup-time.conf /etc/nginx/sites-enabled/default
cp /usr/local/tiledrawer/nginx/status.html /usr/local/tiledrawer/progress/index.html
/etc/init.d/nginx restart

date +'%a %b %d %H:%M:%S %Z %Y Installing software (setup.sh)' >> /usr/local/tiledrawer/progress/status.txt

apt-get -y update
apt-get -y upgrade
apt-get -y install zip unzip gunicorn memcached gdal-bin python-mapnik \
                   python-pip python-imaging python-gevent python-memcache \
                   osm2pgsql postgresql-9.1-postgis openjdk-6-jre-headless \
                   protobuf-compiler libprotobuf-dev libtokyocabinet-dev \
                   libgeos-c1 libgeos-dev python-dev python-psycopg2 \
                   build-essential

ln -s /usr/lib/postgresql/9.1/bin/shp2pgsql /usr/bin/shp2pgsql # really?
ln -s /usr/lib/postgresql/9.1/bin/pgsql2shp /usr/bin/pgsql2shp # seriously?

pip install TileStache ModestMaps Cascadenik shapely imposm.parser imposm

# recent osmosis will have to be done manually,
# use a mirror of http://bretth.dev.openstreetmap.org/osmosis-build/osmosis-0.40.1.tgz
curl -s http://stuff.tiledrawer.com/osmosis-0.40.1.tgz | tar -C /usr/local -xzf -
ln -s /usr/local/osmosis-0.40.1/bin/osmosis /usr/bin/osmosis

mv /etc/memcached.conf /etc/memcached-orig.conf
ln -s /usr/local/tiledrawer/memcached/memcached.conf /etc/memcached.conf
/etc/init.d/memcached restart

#
# Prepare sysctl settings and a better-tuned Postgresql, based on
# Frederik Ramm's 2010 "Optimizing" SOTM talk:
# http://www.geofabrik.de/media/2010-07-10-rendering-toolchain-performance.pdf
#
# Also, move the data dir to ephemeral storage where there's more space.
#

date +'%a %b %d %H:%M:%S %Z %Y Preparing database (setup.sh)' >> /usr/local/tiledrawer/progress/status.txt

/etc/init.d/postgresql stop

/usr/local/tiledrawer/ubuntu/sysctl.sh
mv /etc/sysctl.conf /etc/sysctl-orig.conf
ln -s /usr/local/tiledrawer/ubuntu/etc/sysctl.conf /etc/sysctl.conf

mv /var/lib/postgresql/9.1/main /mnt/var-lib-postgres-9.1-main
ln -s /mnt/var-lib-postgres-9.1-main /var/lib/postgresql/9.1/main

mv /etc/postgresql/9.1/main/postgresql.conf /etc/postgresql/9.1/main/postgresql-orig.conf
mv /etc/postgresql/9.1/main/pg_hba.conf /etc/postgresql/9.1/main/pg_hba-orig.conf
ln -s /usr/local/tiledrawer/postgres/9.1/postgresql.conf /etc/postgresql/9.1/main/postgresql.conf
ln -s /usr/local/tiledrawer/postgres/9.1/pg_hba.conf /etc/postgresql/9.1/main/pg_hba.conf

/etc/init.d/postgresql start

#
# Build ourselves a usable OSM planet database.
#

sudo -u postgres createuser -DRS osm
sudo -u postgres createdb -T template0 -E UTF8 -O osm planet_osm

psql -U postgres planet_osm < /usr/share/postgresql/9.1/contrib/postgis-1.5/postgis.sql
psql -U postgres planet_osm < /usr/share/postgresql/9.1/contrib/postgis-1.5/spatial_ref_sys.sql

echo 'ALTER TABLE geometry_columns OWNER TO osm;' | psql -U postgres planet_osm
echo 'ALTER TABLE spatial_ref_sys OWNER TO osm;' | psql -U postgres planet_osm
