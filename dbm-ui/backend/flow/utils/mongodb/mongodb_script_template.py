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
    "timeout": 3600,
    "account_alias": "root",
    "is_param_sensitive": 0,
}


mongodb_create_actuator_dir_template = """
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
    db.createRole({role:'applyOps',privileges:[{resource:{anyResource:true},actions:["anyAction"]}],roles:[]});
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
mkdir -p {{file_path}}/install/dbactuator-{{uid}}/logs
# debug
exe={{file_path}}/install/mongo-dbactuator
debug_exe={{file_path}}/install/mongo-dbactuator.cyc
if [ -f "$debug_exe" ];then
    cp $debug_exe {{file_path}}/install/dbactuator-{{uid}}/mongo-dbactuator
    echo "using debug version $debug_exe"
else
    cp $exe {{file_path}}/install/dbactuator-{{uid}}
fi

cd {{file_path}}/install/dbactuator-{{uid}}
chmod +x mongo-dbactuator

if [ "{{sudo_account}}" != "root" ];then
  chown {{sudo_account}} {{file_path}}/install/dbactuator-{{uid}} -R
  su {{sudo_account}} -c "./mongo-dbactuator --uid {{uid}} --root_id {{root_id}} --node_id {{node_id}} \
--version_id {{version_id}} --payload {{payload}} --atom-job-list {{action}}"
else
   echo "warning: user == root"
  ./mongo-dbactuator --uid {{uid}} --root_id {{root_id}} --node_id {{node_id}} \
--version_id {{version_id}} --payload {{payload}} --atom-job-list {{action}}
fi
"""


def make_script_common_kwargs(timeout=3600, exec_account="root", is_param_sensitive=0):
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
num=`pgrep prome_exporter_manager |wc -l`
if [[ $num > 0 ]]; then
killall -9 prome_exporter_manager
fi
"""
