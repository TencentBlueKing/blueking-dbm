#!/usr/bin/env bash

repoUser=""
repoPassword=""

tendisplusPkgName="tendisplus-2.6.0-rocksdb-v6.23.3.tgz"
tendisplusPkgMd5="eaf90d7072740fd232b157d9cb32a425"

redisPkgName="redis-6.2.7.tar.gz"
redisPkgMd5="1fc9e5c3a044ce523844a6f2717e5ac3"

#tendisssdPkgName="redis-2.8.17-rocksdb-v1.3.10.tar.gz"
#tendisssdPkgMd5="26fb850222e9666595a48a6f2e9b0382"
tendisssdPkgName="redis-2.8.17-rocksdb-v1.2.20.tar.gz"
tendisssdPkgMd5="7bfe87efbe017c689c3f4a11bb2a8be9"

predixyPkgName="predixy-1.4.0.tar.gz"
predixyPkgMd5="24aba4a96dcf7f8581d2fde89d062455"

twemproxyPkgName="twemproxy-0.4.1-v27.tar.gz"
twemproxyPkgMd5="b7fcec49a43da9fdb5acde0a42287d43"

dbtoolsPkgName="dbtools.tar.gz"
dbtoolsPkgMd5="ced0fa280c63cb31536fefc1845f3ff0"

bkdbmonPkgName="bk-dbmon-v0.12.tar.gz"
bkdbmonPkgMd5="2a3a51c3b4a7dce4300e894e19f2f0ea"

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

localTendisplusPkgName="/data/install/$tendisplusPkgName"
localTendisplusPkgMd5=""

localRedisPkgName="/data/install/$redisPkgName"
localRedisPkgMd5=""

localTendisssdPkgName="/data/install/$tendisssdPkgName"
localTendisssdPkgMd5=""

localPredixyPkgName="/data/install/$predixyPkgName"
localPredixyPkgMd5=""

localTwemproxyPkgName="/data/install/$twemproxyPkgName"
localTwemproxyPkgMd5=""

localDbToolsPkgName="/data/install/$dbtoolsPkgName"
localDbToolsPkgMd5=""

localBkDbmonPkgName="/data/install/$bkdbmonPkgName"
localBkDbmonPkgMd5=""

if [[ -e $localTendisplusPkgName ]]; then

    localTendisplusPkgMd5=$(md5sum $localTendisplusPkgName | awk '{print $1}')
fi

if [[ -e $localRedisPkgName ]]; then
    localRedisPkgMd5=$(md5sum $localRedisPkgName | awk '{print $1}')
fi

if [[ -e $localTendisssdPkgName ]]; then
    localTendisssdPkgMd5=$(md5sum $localTendisssdPkgName | awk '{print $1}')
fi

if [[ -e $localPredixyPkgName ]]; then
    localPredixyPkgMd5=$(md5sum $localPredixyPkgName | awk '{print $1}')
fi

if [[ -e $localTwemproxyPkgName ]]; then
    localTwemproxyPkgMd5=$(md5sum $localTwemproxyPkgName | awk '{print $1}')
fi

if [[ -e $localKeyToolsPkgName ]]; then
    localKeyToolsPkgMd5=$(md5sum $localKeyToolsPkgName | awk '{print $1}')
fi

if [[ -e $localDbToolsPkgName ]]; then
    localDbToolsPkgMd5=$(md5sum $localDbToolsPkgName | awk '{print $1}')
fi

if [[ -e $localBkDbmonPkgName ]]; then
    localBkDbmonPkgMd5=$(md5sum $localBkDbmonPkgName | awk '{print $1}')
fi

wgetCmd="wget --user=$repoUser --password=$repoPassword $repoUrl/tendisplus/Tendisplus-2.6/$tendisplusPkgName -O $localTendisplusPkgName"
if [[ ! -e $localTendisplusPkgName ]]; then
    echo $wgetCmd
    $wgetCmd
elif [[ -n $localTendisplusPkgMd5 && $localTendisplusPkgMd5 != $tendisplusPkgMd5 ]]; then
    echo "rm -f $localTendisplusPkgName"
    rm -f $localTendisplusPkgName
    echo $wgetCmd
    $wgetCmd
fi

wgetCmd="wget --user=$repoUser --password=$repoPassword $repoUrl/predixy/Predixy-latest/$predixyPkgName -O $localPredixyPkgName"
if [[ ! -e $localPredixyPkgName ]]; then
    echo $wgetCmd
    $wgetCmd
elif [[ -n $localPredixyPkgMd5 && $localPredixyPkgMd5 != $predixyPkgMd5 ]]; then
    echo "rm -f $localPredixyPkgName"
    rm -f $localPredixyPkgName
    echo $wgetCmd
    $wgetCmd
fi

wgetCmd="wget --user=$repoUser --password=$repoPassword $repoUrl/redis/Redis-6/$redisPkgName -O $localRedisPkgName"
if [[ ! -e $localRedisPkgName ]]; then
    echo $wgetCmd
    $wgetCmd
elif [[ -n $localRedisPkgMd5 && $localRedisPkgMd5 != $redisPkgMd5 ]]; then
    echo "rm -f $localRedisPkgName"
    rm -f $localRedisPkgName
    echo $wgetCmd
    $wgetCmd
fi

wgetCmd="wget --user=$repoUser --password=$repoPassword $repoUrl/tendisssd/TendisSSD-1.2/$tendisssdPkgName -O $localTendisssdPkgName"
#wgetCmd="wget --user=$repoUser --password=$repoPassword $repoUrl/tendisssd/TendisSSD-1.3/$tendisssdPkgName -O $localTendisssdPkgName"
if [[ ! -e $localTendisssdPkgName ]]; then
    echo $wgetCmd
    $wgetCmd
elif [[ -n $localTendisssdPkgMd5 && $localTendisssdPkgMd5 != $tendisssdPkgMd5 ]]; then
    echo "rm -f $localTendisssdPkgName"
    rm -f $localTendisssdPkgName
    echo $wgetCmd
    $wgetCmd
fi

wgetCmd="wget --user=$repoUser --password=$repoPassword $repoUrl/twemproxy/Twemproxy-latest/$twemproxyPkgName -O $localTwemproxyPkgName"
if [[ ! -e $localTwemproxyPkgName ]]; then
    echo $wgetCmd
    $wgetCmd
elif [[ -n $localTwemproxyPkgMd5 && $localTwemproxyPkgMd5 != $twemproxyPkgMd5 ]]; then
    echo "rm -f $localTwemproxyPkgName"
    rm -f $localTwemproxyPkgName
    echo $wgetCmd
    $wgetCmd
fi

wgetCmd="wget --user=$repoUser --password=$repoPassword $repoUrl/tools/latest/$dbtoolsPkgName -O $localDbToolsPkgName"
if [[ ! -e $localDbToolsPkgName ]]; then
    echo $wgetCmd
    $wgetCmd
elif [[ -n $localDbToolsPkgMd5 && $localDbToolsPkgMd5 != $dbtoolsPkgMd5 ]]; then
    echo "rm -f $localDbToolsPkgName"
    rm -f $localDbToolsPkgName
    echo $wgetCmd
    $wgetCmd
fi

wgetCmd="wget --user=$repoUser --password=$repoPassword $repoUrl/dbmon/latest/$bkdbmonPkgName -O $localBkDbmonPkgName"
if [[ ! -e $localBkDbmonPkgName ]]; then
    echo $wgetCmd
    $wgetCmd
elif [[ -n $localBkDbmonPkgMd5 && $localBkDbmonPkgMd5 != $bkdbmonPkgMd5 ]]; then
    echo "rm -f $localBkDbmonPkgName"
    rm -f $localBkDbmonPkgName
    echo $wgetCmd
    $wgetCmd
fi

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
