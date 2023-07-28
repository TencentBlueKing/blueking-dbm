#!/bin/sh

SCRIPT_DIR=`dirname $0`
cd $SCRIPT_DIR && cd ../frontend || exit 1
npm config set registry https://mirrors.tencent.com/npm/
export NODE_OPTIONS="--max_old_space_size=8192"
npm install . && npm run build
mkdir -p ../static/
cp -rf dist/* ../static/
cd ..
./bin/manage.sh collectstatic --noinput
