#!/usr/bin/env bash

repoUser=""
repoPassword=""

repoUrl=""

usage() {
    echo -e "Usage: $0 [OPTIONS]"
    echo -e "dbactuator test"
    echo -e ""
    echo -e "-H --help -h required,display help info"
    echo -e "--repo-user required,bk repo user name,"
    echo -e "--repo-password required,bk repo user password"
    echo -e "--repo-url required,bk repo https url"
    echo -e ""
    exit 1
}

if [[ $# -lt 2 ]]; then
    usage
fi

for i in "$@"; do
    case $i in
    --repo-user=*)
        repoUser="${i#*=}"
        shift
        ;;
    --repo-password=*)
        repoPassword="${i#*=}"
        shift
        ;;
    --repo-url=*)
        repoUrl="${i#*=}"
        shift
        ;;
    *)
        echo -e "unknown option:$i"
        usage
        ;;
    esac
done

if [[ -z $repoUser ]]; then
    echo -e "error: --repo-user must be passed,repoUser=$repoUser"
    usage
fi

if [[ -z $repoPassword ]]; then
    echo -e "error: --repo-password must be passed,repoPassword=$repoPassword"
    usage
fi

if [[ -z $repoUrl ]]; then
    echo -e "error: --repo-url must be passed,repoUrl=$repoUrl"
    usage
fi

# change dir to current
SCRIPT=$(readlink -f "$0")
DIR=$(dirname $SCRIPT)
cd $DIR
echo "DIR==$DIR"

cd .. && make build

cp ./build/dbactuator_redis /data/install/

# 如果要使用不同版本的集群,就改这里
tendisssdIndexUrl="$repoUrl/tendisssd/TendisSSD-1.2/"
tendisplusIndexUrl="$repoUrl/tendisplus/Tendisplus-2.6/"
redisIndexUrl="$repoUrl/redis/Redis-6/"
predixyIndexUrl="$repoUrl/predixy/Predixy-latest/"
twemproxyIndexUrl="$repoUrl/twemproxy/Twemproxy-latest/"
dbtoolsIndexUrl="$repoUrl/tools/latest/"
bkdbmonIndexUrl="$repoUrl/dbmon/latest/"

wget --user=$repoUser --password=$repoPassword $tendisssdIndexUrl -O  /tmp/tendisssd-latest.html

tendisssdPkgName=$(grep -P --only-match "redis-2.8.17-rocksdb-v\d+.\d+.\d+.tar.gz" /tmp/tendisssd-latest.html|head -1)

if [[ ! -e "/data/install/$tendisssdPkgName" ]]
then
  wget --user=$repoUser --password=$repoPassword $tendisssdIndexUrl/$tendisssdPkgName -O /data/install/$tendisssdPkgName
fi
tendisssdPkgMd5=$(md5sum  /data/install/$tendisssdPkgName| awk '{print $1}')

wget --user=$repoUser --password=$repoPassword $tendisplusIndexUrl -O  /tmp/tendisplus-latest.html

tendisplusPkgName=$(grep -P --only-match "tendisplus-\d+.\d+.\d+-rocksdb-v\d+.\d+.\d+.tgz" /tmp/tendisplus-latest.html|head -1)

if [[ ! -e "/data/install/$tendisplusPkgName" ]]
then
  wget --user=$repoUser --password=$repoPassword $tendisplusIndexUrl/$tendisplusPkgName -O /data/install/$tendisplusPkgName
fi
tendisplusPkgMd5=$(md5sum  /data/install/$tendisplusPkgName| awk '{print $1}')


wget --user=$repoUser --password=$repoPassword $redisIndexUrl -O  /tmp/redis-latest.html

redisPkgName=$(grep -P --only-match "redis-\d+.\d+.\d+.tar.gz" /tmp/redis-latest.html|head -1)

if [[ ! -e "/data/install/$redisPkgName" ]]
then
  wget --user=$repoUser --password=$repoPassword $redisIndexUrl/$redisPkgName -O /data/install/$redisPkgName
fi
redisPkgMd5=$(md5sum  /data/install/$redisPkgName| awk '{print $1}')

wget --user=$repoUser --password=$repoPassword $predixyIndexUrl -O /tmp/predixy-latest.html

predixyPkgName=$(grep -P --only-match "predixy-\d+.\d+.\d+.tar.gz" /tmp/predixy-latest.html|head -1)

if [[ ! -e "/data/install/$predixyPkgName" ]]
then
  wget --user=$repoUser --password=$repoPassword $predixyIndexUrl/$predixyPkgName -O /data/install/$predixyPkgName
fi
predixyPkgMd5=$(md5sum  /data/install/$predixyPkgName| awk '{print $1}')


wget --user=$repoUser --password=$repoPassword $twemproxyIndexUrl -O /tmp/twemproxy-latest.html

twemproxyPkgName=$(grep -P --only-match "twemproxy-\d+.\d+.\d+-v\d+.tar.gz" /tmp/twemproxy-latest.html|head -1)

if [[ ! -e "/data/install/$twemproxyPkgName" ]]
then
  wget --user=$repoUser --password=$repoPassword $twemproxyIndexUrl/$twemproxyPkgName -O /data/install/$twemproxyPkgName
fi
twemproxyPkgMd5=$(md5sum  /data/install/$twemproxyPkgName| awk '{print $1}')


wget --user=$repoUser --password=$repoPassword $dbtoolsIndexUrl -O /tmp/dbtools-latest.html

dbtoolsPkgName=$(grep -P --only-match "dbtools.tar.gz" /tmp/dbtools-latest.html|head -1)

if [[ ! -e "/data/install/$dbtoolsPkgName" ]]
then
  wget --user=$repoUser --password=$repoPassword $dbtoolsIndexUrl/$dbtoolsPkgName -O /data/install/$dbtoolsPkgName
fi
dbtoolsPkgMd5=$(md5sum  /data/install/$dbtoolsPkgName| awk '{print $1}')


wget --user=$repoUser --password=$repoPassword $bkdbmonIndexUrl -O /tmp/dbmon-latest.html

bkdbmonPkgName=$(grep -P --only-match "bk-dbmon-v\d+.\d+.tar.gz" /tmp/dbmon-latest.html|head -1)

if [[ ! -e "/data/install/$bkdbmonPkgName" ]]
then
  wget --user=$repoUser --password=$repoPassword $bkdbmonIndexUrl/$bkdbmonPkgName -O /data/install/$bkdbmonPkgName
fi
bkdbmonPkgMd5=$(md5sum  /data/install/$bkdbmonPkgName| awk '{print $1}')


echo "tendisssdPkgName===>$tendisssdPkgName"
echo "tendisplusPkgName===>$tendisplusPkgName"
echo "redisPkgName===>$redisPkgName"
echo "predixyPkgName==>$predixyPkgName"
echo "twemproxyPkgName==>$twemproxyPkgName"
echo "dbtoolsPkgName==>$dbtoolsPkgName"
echo "bkdbmonPkgName==>$bkdbmonPkgName"

cd $DIR
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o dbactuator-test -v test.go

echo "./dbactuator-test  -tendisplus-pkgname=$tendisplusPkgName -tendisplus-pkgmd5=$tendisplusPkgMd5 
    -redis-pkgname=$redisPkgName -redis-pkgmd5=$redisPkgMd5 
    -tendisssd-pkgname=$tendisssdPkgName -tendisssd-pkgmd5=$tendisssdPkgMd5 
    -predixy-pkgname=$predixyPkgName -predixy-pkgmd5=$predixyPkgMd5 
    -twemproxy-pkgname=$twemproxyPkgName -twemproxy-pkgmd5=$twemproxyPkgMd5
    -dbtools-pkgname=$dbtoolsPkgName -dbtools-pkgmd5=$dbtoolsPkgMd5
    -bkdbmon-pkgname=$bkdbmonPkgName -bkdbmon-pkgmd5=$bkdbmonPkgMd5"

./dbactuator-test \
    -tendisplus-pkgname=$tendisplusPkgName -tendisplus-pkgmd5=$tendisplusPkgMd5 \
    -redis-pkgname=$redisPkgName -redis-pkgmd5=$redisPkgMd5 \
    -tendisssd-pkgname=$tendisssdPkgName -tendisssd-pkgmd5=$tendisssdPkgMd5 \
    -predixy-pkgname=$predixyPkgName -predixy-pkgmd5=$predixyPkgMd5 \
    -twemproxy-pkgname=$twemproxyPkgName -twemproxy-pkgmd5=$twemproxyPkgMd5 \
    -dbtools-pkgname=$dbtoolsPkgName -dbtools-pkgmd5=$dbtoolsPkgMd5 \
    -bkdbmon-pkgname=$bkdbmonPkgName -bkdbmon-pkgmd5=$bkdbmonPkgMd5 \
    -user $repoUser -password $repoPassword -repo-url $repoUrl
