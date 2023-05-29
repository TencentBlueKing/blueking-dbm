#!/usr/bin/env sh
wrapper_log={{.ChecksumInstallPath}}/checksum.log

if [ -e $wrapper_log ]
then
        chown mysql $wrapper_log
        SIZE=$(stat $wrapper_log -c %s)

        if [ $SIZE -gt 100000000 ]
        then
                mv $wrapper_log $wrapper_log.old
                chown mysql $wrapper_log.old
        fi
fi

echo $(date) "begin schedule checksum">>$wrapper_log
chown mysql $wrapper_log

for PORT in "${@:1}"
do
        echo $(date) "schedule port=$PORT">>$wrapper_log
        {{.ChecksumPath}} --config {{.ChecksumInstallPath}}/checksum_$PORT.yaml --mode general --log-file-json --log-file-path {{.ChecksumInstallPath}}/checksum_$PORT.log 1>>$wrapper_log 2>&1 &
done

echo $(date) "all checksum scheduled">>$wrapper_log