#! /usr/bin/bash
rman target sys/{{password}}@{{master}} auxiliary sys/{{password}}@{{slave}} <<EOF
run{
allocate channel prmy1 device type disk connect 'sys/{{password}}@{{master}}';
allocate channel prmy2 device type disk connect 'sys/{{password}}@{{master}}';
allocate channel prmy3 device type disk connect 'sys/{{password}}@{{master}}';
allocate channel prmy4 device type disk connect 'sys/{{password}}@{{master}}';
allocate channel prmy5 device type disk connect 'sys/{{password}}@{{master}}';
allocate channel prmy6 device type disk connect 'sys/{{password}}@{{master}}';
allocate channel prmy7 device type disk connect 'sys/{{password}}@{{master}}';
allocate channel prmy8 device type disk connect 'sys/{{password}}@{{master}}';
allocate auxiliary channel stdy1 device type disk;
allocate auxiliary channel stdy2 device type disk;
allocate auxiliary channel stdy3 device type disk;
allocate auxiliary channel stdy4 device type disk;
allocate auxiliary channel stdy5 device type disk;
allocate auxiliary channel stdy6 device type disk;
allocate auxiliary channel stdy7 device type disk;
allocate auxiliary channel stdy8 device type disk;
sql channel prmy1 "alter system set log_archive_dest_state_{{available_number}}=''enable''";
duplicate target database for standby from active database nofilenamecheck;
sql channel stdy1 "alter database recover managed standby database disconnect";
release channel prmy1;
release channel prmy2;
release channel prmy3;
release channel prmy4;
release channel prmy5;
release channel prmy6;
release channel prmy7;
release channel prmy8;
release channel stdy1;
release channel stdy2;
release channel stdy3;
release channel stdy4;
release channel stdy5;
release channel stdy6;
release channel stdy7;
release channel stdy8;
}
exit
EOF
