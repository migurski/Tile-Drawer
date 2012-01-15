gunicorn
--

gunicorn is what we use to actually serve tiles. Actually, it's a bit more
complicated than that. It works like this:

	internets -> nginx:80 -> gunicorn:8080 -> tilestache -> tiles

gunicorn is run out of init.d; specifically /usr/local/tiledrawer/gunicorn/init.d/tilestache-gunicorn.sh
is symlinked to /etc/init.d/tilestache-gunicorn.sh

The gunicorn server loads the Tilestache:WSGITileServer thingy and serves it on
port 8080. We rely on nginx to proxy traffic from the outside world (port 80) to
gunicorn.

Remember: If you change the configs in /usr/local/tiledrawer/gunicorn/tilestache.cfg
you'll need to restart the gunicorn server using init.d
