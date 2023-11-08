#!/usr/bin/env sh

repoVersion=0.0.1
respGitHash=$(git rev-parse --short HEAD)

# 解析传入的 --version=xxx 和 --git-hash=xxx 参数
while [ $# -gt 0 ]; do
    case "$1" in
    --version=*)
        repoVersion="${1#*=}"
        ;;
    --git-hash=*)
        respGitHash="${1#*=}"
        ;;
    *) ;;
    esac
    shift
done

DIR=$(dirname $0)
cd $DIR

make build VERSION=$repoVersion GITHASH=$respGitHash

cd build

toolVersion=$(./bk-dbmon -v | awk '{print $2}') || ""
targetDir="bk-dbmon-$toolVersion"
tarName="$targetDir.tar"

if [[ ! -d $targetDir ]]; then
    mkdir -p $targetDir
fi

cp ./bk-dbmon $targetDir/
cp ../start.sh $targetDir/
cp ../stop.sh $targetDir/
cp ../dbmon-config.yaml $targetDir/

if [[ -e $tarName ]]; then
    rm -rf $tarName
fi

# 为了保证 tar 压缩得到的包的 md5 一致，这里修改文件的时间戳，同时把 tar -zcf 拆为 tar -cf && gzip
find ${targetDir} -exec touch -t 202301010000 {} +
tar --numeric-owner -cvf ${tarName} $targetDir
gzip -n -f ${tarName}

echo "$tarName success"
