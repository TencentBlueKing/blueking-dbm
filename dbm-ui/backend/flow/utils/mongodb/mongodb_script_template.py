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
mongodb_fast_execute_script_common_kwargs = {
    "timeout": 259200,
    "account_alias": "root",
    "is_param_sensitive": 0,
}

mongodb_create_actuator_dir_template = """
find {{file_path}}/install -mtime +30  -type d -name "dbactuator-*"  |xargs rm -rf
mkdir -p {{file_path}}/install/dbactuator-{{uid}}/logs
cp {{file_path}}/install/mongo-dbactuator {{file_path}}/install/dbactuator-{{uid}}
"""

mongodb_actuator_template = """
cd {{file_path}}/install/dbactuator-{{uid}}
chmod +x mongo-dbactuator
./mongo-dbactuator --uid {{uid}} --root_id {{root_id}} --node_id {{node_id}} \
--version_id {{version_id}} --payload {{payload}} --atom-job-list {{action}}
"""

mongodb_script_template = {"mongodb_actuator_template": mongodb_actuator_template}
mongodb_os_init_actuator_template = """
cd {{file_path}}/install/dbactuator-{{uid}}
chmod +x mongo-dbactuator
./mongo-dbactuator --uid {{uid}} --root_id {{root_id}} --node_id {{node_id}} \
--version_id {{version_id}} --payload {{payload}} --atom-job-list {{action}}  \
--data_dir={{data_dir}}  --backup_dir={{backup_dir}} --user={{user}}  --group={{group}}
"""

mongo_init_set_js_script = """
db = db.getSiblingDB('admin');
var num = db.system.roles.count({'_id':'admin.applyOps'});
if (num == 0) {
    db.createRole({role:'applyOps',privileges:[{resource:{anyResource:true},actions:['anyAction']}],roles:['root']});
    db.grantRolesToUser('dba',[{role:'applyOps',db:'admin'}]);
    db.grantRolesToUser('appdba',[{role:'applyOps',db:'admin'}]);
}
var num = db.system.roles.count({'_id':'admin.heartbeatOps'});
if (num == 0) {
    db.createRole({role:'heartbeatOps',privileges:[{resource:{db:'admin',collection:'gcs_heartbeat'},
actions:['find','insert','update','remove']}],roles:[]});
    db.grantRolesToUser('monitor',[{role:'heartbeatOps',db:'admin'}]);
}
var v = db.version();
if (v.match(/^3\\./)) {
    db.system.version.insert({ '_id' : 'authSchema', 'currentVersion' : 3 });
}
"""

mongo_extra_manager_user_create_js_script = """
db = db.getSiblingDB('admin');
var v = db.version();
var main = v.slice(0,3);
var float_main = parseFloat(main);
var num = db.system.users.count({'_id' : 'admin.appdba'});
if (num == 0) {
    if (float_main >= 2.6) {
        db.createUser({user:'appdba',pwd:'{{appdba_pwd}}',
        roles:[{role:'userAdminAnyDatabase',db:'admin'},{role:'dbAdminAnyDatabase',db:'admin'},
        {role:'readWriteAnyDatabase',db:'admin'},{role:'clusterAdmin',db:'admin'}]});
    } else {
        db.addUser({user:'appdba',pwd:'{{appdba_pwd}}',
        roles:['userAdminAnyDatabase','dbAdminAnyDatabase','readWriteAnyDatabase','clusterAdmin']});
    }
}
var num =  db.system.users.count({'_id' : 'admin.monitor'});
if (num == 0) {
    if (float_main >= 2.6) {
        db.createUser({user:'monitor',pwd:'{{monitor_pwd}}',
        roles:[{role:'backup',db:'admin'},{role:'clusterMonitor',db:'admin'},
        {role:'readAnyDatabase',db:'admin'},{role:'hostManager',db:'admin'}]});
    } else {
        db.addUser({user:'monitor',pwd:'{{monitor_pwd}}',
        roles:['clusterAdmin','readAnyDatabase','dbAdminAnyDatabase','userAdminAnyDatabase']});
    }
}
var num =  db.system.users.count({'_id' : 'admin.appmonitor'});
if (num == 0) {
    if (float_main >= 2.6) {
        db.createUser({user:'appmonitor',pwd:'{{appmonitor_pwd}}',
        roles:[{role:'backup',db:'admin'},{role:'clusterMonitor',db:'admin'},
        {role:'readAnyDatabase',db:'admin'},{role:'hostManager',db:'admin'}]});
    } else {
        db.addUser({user:'appmonitor',pwd:'{{appmonitor_pwd}}',
        roles:['clusterAdmin', 'readAnyDatabase', 'dbAdminAnyDatabase', 'userAdminAnyDatabase']});
    }
}
"""

# mongodb_actuator_template2 run dbactuator by sudo_account
mongodb_actuator_template2 = """
#!/bin/sh
# mongodb actuator script

# safe_remove_dbactuator_dir
function safe_remove_dbactuator_dir() {
    local install_dir=$1
    if [ ! -d $install_dir ];then
        echo "Error install_dir $install_dir not exist"
        return
    fi
    for old_dir in `find $install_dir -maxdepth 1  -type d -name "dbactuator-*"  -mtime +3  -print`
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

install_dir=$file_path/install
workdir=$install_dir/dbactuator-$uid
exe=mongo-dbactuator
exe_path=$workdir/$exe
lock_file="$workdir/$exe.cp.lock"
mkdir -p $workdir/logs

safe_remove_dbactuator_dir $install_dir
safe_cpfile $install_dir/$exe $exe_path $lock_file

common_args="--uid $uid --root_id $root_id --node_id $node_id --version_id $version_id"
cmd="./mongo-dbactuator $common_args --payload $payload --atom-job-list $action"

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


def make_script_common_kwargs(timeout=259200, exec_account="root", is_param_sensitive=0):
    """
    make_script_common_kwargs 生成脚本执行的公共参数
    """
    return {
        "timeout": timeout,
        "account_alias": exec_account,
        "is_param_sensitive": is_param_sensitive,
    }


def prepare_recover_dir_script(dest_dir: str) -> str:
    if not dest_dir.startswith("/data/dbbak"):
        raise Exception("dest_dir must start with /data/dbbak")

    script = """
# todo add root id and node id
set -x
mkdir -p {}
echo return code $?
chown -R {} {}
echo return code $?"""
    return script.format(dest_dir, "mysql", dest_dir)


# 关闭老的dbmon
mongodb_stop_old_dbmon_script = """
source /home/mysql/.bash_profile
/home/mysql/dbmon/stop.sh
/home/mysql/filebeat-deploy/remove
/home/mysql/filebeat-deploy/stop_watcher
/home/mysql/filebeat-deploy/stop_filebeat
killall -9 prome_exporter_manager | echo true
"""

# 分片集群初始化设置
mongodb_cluster_inti_js_script = """
sh.setBalancerState(false);
db.getSisterDB('config').settings.save({ _id:'chunksize', value: 512 });
"""

# 禁用bk-dbmon 监控
mongodb_dbmon_shield_port = """
cd /home/mysql/bk-dbmon
/home/mysql/bk-dbmon/bk-dbmon alarm shield --port {{port}}
"""

# 解禁bk-dbmon 监控
mongodb_dbmon_unblock_port = """
cd /home/mysql/bk-dbmon
/home/mysql/bk-dbmon/bk-dbmon alarm unblock --port {{port}}
"""

# 删除bk-dbmon 监控
mongodb_dbmon_delete_port = """
cd /home/mysql/bk-dbmon
/home/mysql/bk-dbmon/bk-dbmon meta delete --port  {{port}}
"""
