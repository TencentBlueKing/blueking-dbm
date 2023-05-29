#!/bin/bash
# to connect to mongo db, usage: conn.sh $port [cmd], if port is all, will exec on all servers.
# if cmd is not set, will connect to mongo shell, otherwise will exec the cmd.
# if cmd is set, the cmd should be a mongo shell command, like "db.getCollectionNames()"

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
conf=$SCRIPT_DIR/dbmon-config.yaml

port=$1
shift

gojq=$SCRIPT_DIR/gojq
if [ ! -f $gojq ];then
  echo "gojq not exists"
  exit;
fi

if [ ! "$port"  ];then
	echo "bad port, usage: $0 $port [cmd], if port is all, will exec on all servers."
	exit;
fi

if [ ! -f $conf ];then
  echo "config file not exists"
  exit;
fi

function exec_port(){
  port=$1
  shift
  user=`$gojq -r --yaml-input  ".servers[] | select(.port == $port) | .username" $conf`
  pass=`$gojq -r --yaml-input  ".servers[] | select(.port == $port) | .password" $conf`

  if [ -z "$user"  ];then
  	echo may be $port not exists
  	exit;
  fi

  if [ -n "$*" ];then
  	echo exec mongo --port $port admin -u$user -pxxx --eval "$*"
  	mongo --quiet --port $port admin -u"$user" -p"$pass" --eval "$*"
  else
  	echo exec mongo --port $port admin -u$user -pxxx
  	mongo --quiet --port $port admin -u"$user" -p"$pass"
  fi
}

if [ "$port" == "all" ];then
  for port in `$SCRIPT_DIR/gojq -r --yaml-input  ".servers[].port" $conf`;do
    exec_port $port $@
  done
  exit;
else
  exec_port $port $@
fi

# todo add more short cut command:
# 1. status
# 2. dbs
