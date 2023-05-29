#!/bin/bash

# release txsql and community dbbackup-go-XXX.tar.gz
# need run in current dir

depsDir=dbbackup-go-deps
function build_package() {
  rm -rf $depsDir
  tar -zxf dbbackup-go-deps-${1}.tar.gz && mv dbbackup-go-deps-${1} $depsDir
  if [ $? -gt 0 ];then
    echo "release package for $1 failed: tar"
    exit 1
  fi
  # skip go build, we hope txsql/community has the same dbbackup binary
  make package VERSION=$VERSION DIST=$1
}

# txsql
echo
echo "#################### build txsql ####################"
echo "build package for txsql..."
[ -f dbbackup-go-deps-txsql.tar.gz ] && build_package txsql
[ $? -gt 0 ] && exit 1
ls -l build/dbbackup-go-txsql.tar.gz

# community
echo
echo "#################### build community ####################"
echo "build package for community..."
[ -f dbbackup-go-deps-community.tar.gz ] && build_package community
[ $? -gt 0 ] && exit 1
ls -l build/dbbackup-go-community.tar.gz