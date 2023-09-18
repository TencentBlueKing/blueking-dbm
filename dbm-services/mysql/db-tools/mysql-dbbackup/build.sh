#!/bin/bash

# release_type only used for release package name
# we use dependency dir 'dbbackup-go-deps/' to tar, so make sure this dir has correct deps

#### precheck section
usage() {
  echo "Usage:"
  echo "./build.sh [-s] [-t your_release_type]"
  echo -e "Description:\n"
  echo "  -s: skip go build, use build/dbbackup binary"
  echo "  -t: set release_type, allowed: txsql,community"
  echo ""
  exit 1
}

release_type=""
go_build=1
while getopts 't:sh' OPT; do
    case $OPT in
        t)
          release_type="$OPTARG"
          ;;
        s)
          go_build=0
          ;;
        h) usage;;
        ?) usage;;
    esac
done
if [ "$release_type" != "txsql" -a "$release_type" != "community" ];then
  echo "unknown release_type. allowed: txsql,community"
  exit 1
else
  echo "release_type=$release_type"
fi

#### build section
proj_bin=dbbackup
build_dir=build
proj=dbbackup-go
pkg_dir=${build_dir}/${proj}
proj_pkg=${proj}-${release_type}.tar.gz

if [ $go_build -ne 0 ];then
  echo "run go build"
  rm -rf $pkg_dir ; mkdir -p $pkg_dir
  rm -f ${build_dir}/${proj_bin}
  go build -o ${build_dir}/${proj_bin}
  if [ $? -gt 0 ];then
    echo "build dbbackup failed"
    exit 1
  fi
else
  echo "skip run go build. use binary build/dbbackup"
  rm -rf $pkg_dir ; mkdir -p $pkg_dir
  if [ ! -f ${build_dir}/${proj_bin} ];then
    echo "${build_dir}/${proj_bin} not exists"
    exit 1
  fi
fi

cp -r dbbackup-go-deps/* ${pkg_dir}/
if [ $? -gt 0 ];then
  echo "copy dbbackup-go-deps failed"
  exit 1
fi

cp -a dbbackup_main.sh ${pkg_dir}/
cp -a mydumper_for_tdbctl.cnf ${pkg_dir}/
cp -a ${build_dir}/${proj_bin} ${pkg_dir}/
chmod +x ${pkg_dir}/*.sh && chmod +x ${pkg_dir}/dbbackup
chmod +x ${pkg_dir}/bin/* && chmod +x ${pkg_dir}/bin/*/*

tar -C ${build_dir} -zcvf ${build_dir}/${proj_pkg} ${proj}
