#!/bin/bash
# to connect to mongo db, usage: conn.sh $port [shell|mongo|mongosh] [cmd], if port is all, will exec on all servers.
# if cmd is not set, will connect to mongo shell, otherwise will exec the cmd.
# if cmd is set, the cmd should be a mongo shell command, like "db.getCollectionNames()"

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
conf=$SCRIPT_DIR/dbmon-config.yaml

port=$1

gojq=$SCRIPT_DIR/gojq
if [ ! -f $gojq ];then
  echo "gojq not exists"
  exit;
fi

if [ ! "$port"  ];then
	echo "bad port, usage: $0 $port [cmd], if port is all, will exec on all servers."
	exit;
fi
shift

mongo_bin=mongo
if [ "$1" == "shell" ];then
  shift
elif [ "$1" == "mongo" ];then
  mongo_bin=mongo
  shift
elif [ "$1" == "mongosh" ];then
  mongo_bin=mongosh
  shift
fi

if [ ! -f $conf ];then
  echo "config file not exists"
  exit;
fi

function get_mongo_bin(){
  bin=$1
  if command -v "$bin" >/dev/null 2>&1;then
    command -v "$bin"
  elif [ -x "/home/mysql/dbtools/$bin" ];then
    echo "/home/mysql/dbtools/$bin"
  elif [ -x "/usr/local/mongodb/bin/$bin" ];then
    echo "/usr/local/mongodb/bin/$bin"
  else
    echo "$bin"
  fi
}

function exec_port(){
  port=$1
  shift
  user=`$gojq -r --yaml-input  ".servers[] | select(.port == $port) | .username" $conf`
  pass=`$gojq -r --yaml-input  ".servers[] | select(.port == $port) | .password" $conf`
  mongo_cmd=`get_mongo_bin $mongo_bin`

  if [ -z "$user"  ];then
  	echo may be $port not exists
  	exit;
  fi

  if [ -n "$*" ];then
  	echo exec $mongo_cmd --port $port admin -u$user -pxxx --eval "$*"
  	$mongo_cmd --quiet --port $port admin -u"$user" -p"$pass" --eval "$*"
  else
  	echo exec $mongo_cmd --port $port admin -u$user -pxxx
  	$mongo_cmd --quiet --port $port admin -u"$user" -p"$pass"
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
