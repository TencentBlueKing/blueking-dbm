#!/usr/bin/env sh

repoVersion=0.0.1
respGitHash=$(git rev-parse --short HEAD)
respGitDate=202301010000

# 解析传入的 --version=xxx 和 --git-hash=xxx 参数
while [ $# -gt 0 ]; do
    case "$1" in
    --version=*)
        repoVersion="${1#*=}"
        ;;
    --git-hash=*)
        respGitHash="${1#*=}"
        ;;
    --git-date=*)
        respGitDate="${1#*=}"
        ;;
    *) ;;
    esac
    shift
done

DIR=$(dirname $0)
cd $DIR

make build VERSION=$repoVersion GITHASH=$respGitHash

cd package

targetDir="bk-dbmon"
tarName="$targetDir-mg.tar"

if [[ ! -d $targetDir ]]; then
    mkdir -p $targetDir
fi

cp ../build/bk-dbmon $targetDir/
cp start.sh stop.sh gojq conn.sh $targetDir/
chmod +x $targetDir/*.sh $targetDir/gojq $targetDir/bk-dbmon


if [[ -e $tarName ]]; then
    rm -rf $tarName
fi




# 为了保证 tar 压缩得到的包的 md5 一致，这里修改文件的时间戳，同时把 tar -zcf 拆为 tar -cf && gzip
find ${targetDir} -exec touch -t $respGitDate {} +
tar --numeric-owner --no-xattrs -cvf ${tarName} $targetDir
gzip -n -f ${tarName}

if [[ -e $targetDir ]]; then
    rm -rf $targetDir
fi

echo "$tarName.gz success"
