#!/bin/sh -ex

curl -sL https://github.com/downloads/mapnik/mapnik/mapnik-2.0.0.tar.bz2 | bzcat | tar -C /usr/local/tiledrawer/progress -xf -

cd /usr/local/tiledrawer/progress/mapnik-2.0.0

python scons/scons.py configure
python scons/scons.py -j2
python scons/scons.py install

ldconfig
