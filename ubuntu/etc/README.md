Basically each of the files in the 'etc' folder should be symlinked to the
respective places in the actual /etc directory.

Do NOT blindly symlink folders. That would be wrong and will make you cry. Just
go through and symlink each file individually. It's a (tiny) pain but it's not
like you'll be doing it every day. If you are that also means you've got bigger
problems.

If you look carefully you'll see there is both a sysctl.sh script and a
etc/sysctl.conf file (in the etc folder).

They contain the same settings. The shell script is there for you to run when
the machine is (re)built and the config file is there so the settings persist
across system reboots. The config file should be symlinked in to /etc

These settings are from John Allspaw circa May 2010 and are "what we
do at Etsy, and what we did at Flickr for a basic webserver". Which seems like
as a good a place to start as any.

