#! /usr/bin/bash
rman target sys/{{password}}@{{master}} auxiliary sys/{{password}}@{{slave}} <<EOF
run{
allocate channel prmy1 device type disk connect 'sys/{{password}}@{{master}}';
allocate channel prmy2 device type disk connect 'sys/{{password}}@{{master}}';
allocate auxiliary channel stdy1 device type disk;
allocate auxiliary channel stdy2 device type disk;
sql channel prmy1 "alter system set log_archive_dest_state_{{available_number}}=''enable''";
duplicate target database for standby from active database nofilenamecheck;
sql channel stdy1 "alter database recover managed standby database disconnect";
release channel prmy1;
release channel prmy2;
release channel stdy1;
release channel stdy2;
}
exit
EOF
