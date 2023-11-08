#!/usr/bin/env sh

DIR=$(dirname $0)
cd $DIR

make build

cd build

version=$(./bk-dbmon -v | awk '{print $2}') || ""
targetDir="bk-dbmon-$version"
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
