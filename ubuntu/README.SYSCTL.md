If you look carefully you'll see there is both a sysctl.sh script and a
etc/sysctl.conf file (in the etc folder).

They contain the same settings. The shell script is there for you to run when
the machine is (re)built and the config file is there so the settings persist
across system reboots. The config file should be symlinked in to /etc

These settings are from John Allspaw circa May 2010 and are "what we
do at Etsy, and what we did at Flickr for a basic webserver". Which seems like
as a good a place to start as any.

Also: make sure you read the README.md file in the 'etc' directory.
