#!/bin/sh -ex

#
# Start TileStache under gunicorn, and switch nginx configuration to tile proxy.
#

ln -s /usr/local/tiledrawer/gunicorn/init.d/tilestache-gunicorn.sh /etc/init.d/tilestache-gunicorn.sh
/etc/init.d/tilestache-gunicorn.sh start

ln -sf /usr/local/tiledrawer/nginx/drawer-time.conf /etc/nginx/sites-enabled/default
/etc/init.d/nginx restart
