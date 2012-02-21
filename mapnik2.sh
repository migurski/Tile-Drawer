#!/bin/sh -ex

# use a mirror of https://github.com/downloads/mapnik/mapnik/mapnik-2.0.0.tar.bz2
curl -sL http://stuff.tiledrawer.com/mapnik-2.0.0.tar.bz2 | bzcat | tar -C /usr/local/tiledrawer/progress -xf -

cd /usr/local/tiledrawer/progress/mapnik-2.0.0

python scons/scons.py configure
python scons/scons.py -j2
python scons/scons.py install

ldconfig
