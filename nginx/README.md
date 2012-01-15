nginx
--

We use nginx to proxy requests on port 80 to a TileStache server running under
gunicorn. See the README file in the 'gunicorn' folder for details.

Symlink /usr/local/tilefarm.conf in to /etc/nginx/sites-enabled/ and restart nginx
