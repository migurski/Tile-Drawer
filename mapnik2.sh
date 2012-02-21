#!/bin/sh -ex

# https://github.com/mapnik/mapnik/wiki/UbuntuInstallation/55cf72
apt-get -y install g++ cpp libicu-dev \
                   libboost-filesystem1.46-dev libboost-iostreams1.46-dev \
                   libboost-program-options1.46-dev libboost-python1.46-dev \
                   libboost-regex1.46-dev libboost-system1.46-dev \
                   libboost-thread1.46-dev \
                   python-dev python-nose libxml2 libxml2-dev libfreetype6 \
                   libfreetype6-dev libjpeg62 libjpeg62-dev libltdl7 libltdl-dev \
                   libpng12-0 libpng12-dev libgeotiff-dev libtiff4 libtiff4-dev \
                   libtiffxx0c2 libcairo2 libcairo2-dev python-cairo python-cairo-dev \
                   libcairomm-1.0-1 libcairomm-1.0-dev ttf-unifont ttf-dejavu \
                   ttf-dejavu-core ttf-dejavu-extra subversion build-essential \
                   libgdal1-dev python-gdal postgresql-9.1 postgresql-server-dev-9.1 \
                   postgresql-contrib-9.1 postgresql-9.1-postgis libsqlite3-dev

# use a mirror of https://github.com/downloads/mapnik/mapnik/mapnik-2.0.0.tar.bz2
curl -sL http://stuff.tiledrawer.com/mapnik-2.0.0.tar.bz2 | bzcat | tar -C /usr/local/tiledrawer/progress -xf -

cd /usr/local/tiledrawer/progress/mapnik-2.0.0

python scons/scons.py configure
python scons/scons.py -j2
python scons/scons.py install

ldconfig
