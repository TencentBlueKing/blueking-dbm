#!/bin/sh
# 新建riak用户
##
# riak scripts
##
# depends: ~/abs/ssh.exp  ~/abs/scp.exp

add_user () {
  id riak >& /dev/null
  if [ $? -ne 0 ]
  then
          useradd riak -u498
  else
          echo "user riak exists" 1>&2
          rm $0
          exit 1
  fi
}

change_os () {
echo "vm.dirty_background_ratio = 0
vm.dirty_background_bytes = 104857600
vm.dirty_ratio = 0
vm.dirty_bytes = 209715200
vm.dirty_writeback_centisecs = 100
vm.dirty_expire_centisecs = 200
vm.swappiness = 0
net.ipv4.tcp_max_syn_backlog = 40000
net.core.somaxconn = 40000
net.core.wmem_default = 8388608
net.core.rmem_default = 8388608
net.ipv4.tcp_sack = 1
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_moderate_rcvbuf = 1" >> /etc/sysctl.conf
/sbin/sysctl -p
}

mk_riakdir () {
  mkdir -p /data/install
  chmod -R a+rwx /data/install
  mkdir -p /data/riakenv
  mkdir -p /data/riak/log
  chown -R riak.root /data/riak/log
  mkdir /etc/riak/
}

init_riak () {
  add_user
  change_os
  mk_riakdir
}

init_riak
rm $0
exit