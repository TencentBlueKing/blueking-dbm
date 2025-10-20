# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
# fast_execute_script接口固定参数
# 这里独立出来，遇到过全局变量被其他db修改，导致用户错乱的问题
redis_fast_execute_script_common_kwargs = {
    "timeout": 10800,
    "account_alias": "root",
    "is_param_sensitive": 0,
}

redis_actuator_template = """
find /home/mysql/install/dbactuator-*/ -mtime +30  -type d -name "dbactuator-*"  |xargs rm -rf
mkdir -p {{data_dir}}/install/dbactuator-{{uid}}/logs
chmod +x {{data_dir}}/install/dbactuator_redis
cd {{data_dir}}/install/dbactuator-{{uid}}
{{data_dir}}/install/dbactuator_redis --uid {{uid}} --root_id {{root_id}} --node_id {{node_id}} \
--version_id {{version_id}} --payload {{payload}} --atom-job-list {{action}}
"""


redis_data_structure_payload_template = """
{{payload}}
"""

redis_data_structure_actuator_template = """
find /home/mysql/install/dbactuator-*/ -mtime +40  -type d -name "dbactuator-*"  |xargs rm -rf
mkdir -p {{data_dir}}/install/dbactuator-{{uid}}/logs
chmod +x {{data_dir}}/install/dbactuator_redis
cd {{data_dir}}/install/dbactuator-{{uid}}
{{data_dir}}/install/dbactuator_redis --uid {{uid}} --root_id {{root_id}} --node_id {{node_id}} \
--version_id {{version_id}} --payload_file={{data_dir}}/install/{{file_name}} --atom-job-list {{action}}
"""


def make_script_common_kwargs(timeout=259200, exec_account="root", is_param_sensitive=0):
    """
    make_script_common_kwargs 生成脚本执行的公共参数
    """
    return {
        "timeout": timeout,
        "account_alias": exec_account,
        "is_param_sensitive": is_param_sensitive,
    }


# redis_actuator_template2 run dbactuator by sudo_account
redis_actuator_template2 = """
#!/bin/sh
# redis actuator script

# safe_remove_dbactuator_dir
function safe_remove_dbactuator_dir() {
    local install_dir=$1
    if [ ! -d $install_dir ];then
        echo "Error install_dir $install_dir not exist"
        return
    fi
    for old_dir in `find $install_dir -maxdepth 1  -type d -name "dbactuator-*"  -mtime +15  -print`
    do
        if [  "${old_dir/dbactuator//}" = "$old_dir" ];then
            echo "Error bad dir $old_dir"
            continue
        fi
        if [ -d $old_dir ];then
            echo "Removing old dbactuator dir $old_dir"
            rm -rf $old_dir || {echo Error Removing old dbactuator dir $old_dir}
        fi
    done
}

# safe_cpfile function.
function safe_cpfile() {
    local src_file=$1
    local dst_file=$2
    local lock_file=$3
    if [ ! -f "$src_file" ];then
         echo "Source file $src_file does not exist. Exiting."
         exit 1
    fi
    (
       flock -w 30 200 || { echo "Another process is holding the lock. Exiting."; exit 1; }
       if [[ ! -f "$dst_file" ]];then
          echo "Copying $src_file to $dst_file"
          cp $src_file $dst_file
          if [[ $? -ne 0 ]];then
                echo "Error copying $src_file to $dst_file"
                exit 1
          fi
       else
          diff $src_file $dst_file > /dev/null
          if [[ $? -ne 0 ]];then
             echo "Copying $src_file to $dst_file"
             cp $src_file $dst_file
             if [[ $? -ne 0 ]];then
                echo "Error copying $src_file to $dst_file"
                exit 1
             fi
          else
             echo "$src_file and $dst_file are the same. No need to copy."
          fi
       fi
    )  200>"$lock_file"
}

# replace var
sudo_account={{sudo_account}}
file_path={{file_path}}
uid={{uid}}
root_id={{root_id}}
node_id={{node_id}}
version_id={{version_id}}
payload='{{payload}}'
action={{action}}

if [ -z "$file_path" -o "$file_path" == "/" ];then
    echo "Error file_path is empty or /"
    exit 1
fi

exe=dbactuator_redis
install_dir=$file_path/install
workdir=$install_dir/dbactuator-$uid
exe_path=$workdir/$exe
lock_file="$workdir/$exe.cp.lock"
mkdir -p $workdir/logs

# update workdir to avoid find and remove old dbactuator dir
if [ -d "$workdir" ];then
    touch $workdir
fi

safe_remove_dbactuator_dir $install_dir
safe_cpfile $install_dir/$exe $exe_path $lock_file

common_args="--uid $uid --root_id $root_id --node_id $node_id --version_id $version_id"
cmd="./$exe $common_args --payload $payload --atom-job-list $action"

cd $workdir || { echo "Error cd $workdir"; exit 1; }
chmod +x $exe
if [ "$sudo_account" != "root" ];then
   echo "user == $sudo_account"
   chown $sudo_account $workdir -R
   su $sudo_account -c "$cmd"
else
   echo "user == root"
   $cmd
fi
"""
