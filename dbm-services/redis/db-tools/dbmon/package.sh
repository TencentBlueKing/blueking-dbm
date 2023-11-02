#!/usr/bin/env sh

DIR=$(dirname $0)
cd $DIR

make build

cd build

version=$(./bk-dbmon -v | awk '{print $2}')
targetDir="bk-dbmon-$version"
tarName="$targetDir.tar.gz"

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

tar --remove-files -zcf $tarName $targetDir

echo "$tarName success"
