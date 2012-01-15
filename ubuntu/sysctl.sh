#!/bin/sh

# "this is what we do at etsy, and what we did at flickr
# for a basic webserver" (allspaw/20100518)

sysctl -w kernel.panic=1
sysctl -w kernel.shmmax=2147483648
sysctl -w net.ipv4.conf.eth0.rp_filter=0
sysctl -w net.ipv4.tcp_fin_timeout=30
sysctl -w net.ipv4.tcp_retrans_collapse=0
sysctl -w net.ipv4.tcp_syncookies=1
sysctl -w net.ipv4.tcp_tw_recycle=1
sysctl -w vm.overcommit_ratio=90
sysctl -w vm.overcommit_memory=2
sysctl -w kernel.core_uses_pid=1
sysctl -w net.core.rmem_max=16777216
sysctl -w net.core.wmem_max=16777216
sysctl -w net.ipv4.tcp_rmem='4096 87380 16777216'
sysctl -w net.ipv4.tcp_wmem='4096 65536 16777216'
sysctl -w net.ipv4.tcp_timestamps=0
sysctl -w net.core.netdev_max_backlog=2500