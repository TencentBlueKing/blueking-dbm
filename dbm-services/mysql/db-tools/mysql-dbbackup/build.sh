#!/bin/bash

proj_bin=dbbackup
build_dir=build
proj=dbbackup-go
pkg_dir=${build_dir}/${proj}
proj_pkg=${proj}.tar.gz

rm -rf build/dbbackup-go

go build -o ${pkg_dir}/${proj_bin}
if [ $? -gt 0 ];then
  echo "build dbbackup failed"
  exit 1
fi

cp -r lib ${pkg_dir}/
cp -r bin ${pkg_dir}/
cp dbbackup_main.sh ${pkg_dir}/
chmod +x ${pkg_dir}/*.sh && chmod +x ${pkg_dir}/dbbackup
chmod +x ${pkg_dir}/bin/* && chmod +x ${pkg_dir}/bin/*/*

tar -C ${build_dir} -zcvf ${build_dir}/${proj_pkg} ${proj}
