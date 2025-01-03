#!/bin/sh

SCRIPT_DIR=`dirname $0`
cd $SCRIPT_DIR && cd ../frontend || exit 1
npm config set registry https://mirrors.tencent.com/npm/
export NODE_OPTIONS="--max_old_space_size=8192"
yarn install && yarn build
mkdir -p ../static/
cp -rf dist/* ../static/
cd ..
# 单独处理 monacoeditorwork
rm -rf ./static/monacoeditorwork
mv ./static/static/monacoeditorwork ./static/monacoeditorwork
./bin/manage.sh collectstatic --noinput
