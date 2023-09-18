#!/bin/sh

export PATH=/usr/local/mysql/bin:$PATH
scriptDir=$(dirname "$0")
scriptName=$(basename "$0")

if [ $scriptDir = "." ];then
  scriptDir=`pwd`
elif [[ ! "$scriptDir" =~ ^/.* ]];then
  echo "please run $scriptName in correct path"
  exit 1
fi

# work_dir
cd $scriptDir && mkdir -p logs || exit 1

logfile=${scriptDir}/logs/dbbackup.log
if [ -e $logfile ]
then
        SIZE=`stat $logfile -c %s`;
        if [ $SIZE -gt 100000000 ]
        then
                mv $logfile $logfile.old
        fi
fi

usage() {
  echo "Usage:"
  echo "./dbbackup_main.sh [-p 20000,20001] [-k your-backup-id] [-l your-bill-id] [-t your-backup-type]"
  echo -e "Description:\n"
  echo -e "  -p: port list to backup, comma separated. Will find backup config file by dbbackup.<port>.ini."
  echo "      find -regex '.*dbbackup\.[0-9]+\.ini' if -p not given"
  echo "  -k: set backup-id to dbbackup cmd, will overwrite Public.BackupId"
  echo "  -l: set bill-id to dbbackup cmd, will overwrite Public.BillId"
  echo "  -t: set backup-type to dbbackup cmd, will overwrite Public.BackupType"
  echo ""
  exit 1
}

Ports=""
configFiles=""
dbbackupOpt=""
while getopts 'p:k:l:t:h' OPT; do
    case $OPT in
        p)
          Ports="$OPTARG"
          Ports=${Ports//,/ }
          ;;
        k)
          BackupId="$OPTARG"
          dbbackupOpt="$dbbackupOpt --backup-id=$BackupId"
          ;;
        l)
          BillId="$OPTARG"
          dbbackupOpt="$dbbackupOpt --bill-id=$BillId"
          ;;
        t)
          BackupType="$OPTARG"
          dbbackupOpt="$dbbackupOpt --backup-type=$BackupType"
          ;;
        h) usage;;
        ?) usage;;
    esac
done
#shift $((OPTIND-1))
#Ports="$@"

get_config_files() {
  if [ -z "$Ports" ];then
    configFiles=`find $scriptDir -maxdepth 1 -regex ".*dbbackup\.[0-9]+\.ini"`
  else
    for port in $Ports; do
      fname=dbbackup.${port}.ini
      if [ -e "${scriptDir}/${fname}" ];then
        configFiles="${configFiles} $fname"
      else
        echo "file $fname not found for port $port" >&2
        exit 1
      fi
    done
  fi
  if [ -z $configFiles ];then
    echo -e "Error: no config files found\n" >&2
    usage
  fi
}

get_config_files

echo "begin mutli dbbackup" >>$logfile
errPorts=""
okPorts=""
for conf_file in $configFiles
do
    #port=`echo $conf_file |awk -F. '{print $(NF-1)}'`
    port=`grep MysqlPort $conf_file |head -1|grep -v "#" |cut -d= -f2`
    echo "now doing dbbackup for config file=$conf_file port=$port"
    echo "${scriptDir}/dbbackup dumpbackup --config=$conf_file $dbbackupOpt 2>&1 >> $logfile"
    ${scriptDir}/dbbackup dumpbackup --config=$conf_file $dbbackupOpt 2>&1 >> $logfile
    if [ $? -eq 0 ];then
      okPorts="$okPorts $port"
    else
      errPorts="$errPorts $port"
    fi
done
# 输出可用于判断哪些 ports 成功，哪些失败
echo "okPorts:$okPorts,errPorts:$errPorts"
if [ -n "$errPorts" ];then
  echo "ports backup failed: $errPorts" >&2
  exit 1
fi