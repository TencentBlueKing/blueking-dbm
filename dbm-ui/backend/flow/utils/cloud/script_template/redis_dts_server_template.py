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
# 启用redis dts_server的脚本
__all__ = ["start_redis_dts_server_template", "stop_redis_dts_server_template"]

start_redis_dts_server_template = """
chmod a+x /data/install/dbactuator_redis
cd /data/install && ./dbactuator_redis  --uid=1111 --root_id=2222 --node_id=3333 --version_id=v1 \
--atom-job-list="sysinit" --payload="{{sys_init_paylod}}"

source /etc/profile

dns_servers="{{dns_servers}}"
while read -r line
do
    # skip empty line
    if [[ "$line" =~ ^[[:space:]]*$ ]]; then
        continue
    fi
    if ! grep -qF "$line" /etc/resolv.conf; then
        sed -i "1i $line" /etc/resolv.conf
        echo "Added: $line"
    else
        echo "Skipped: $line"
    fi
done <<< "$dns_servers"

bk_dbm_nginx_url="{{bk_dbm_nginx_url}}"
bk_dbm_cloud_id="{{bk_dbm_cloud_id}}"
bk_dbm_cloud_token="{{bk_dbm_cloud_token}}"
system_user="{{system_user}}"
system_password="{{system_password}}"
city_name="{{city_name}}"
warning_msg_notifiers="{{warning_msg_notifiers}}"

dts_server_tool="redis_dts_server"

dts_parent_dir="$REDIS_DATA_DIR/dbbak"
dts_server_dir="$dts_parent_dir/redis_dts"

new_dts_pkg="/data/install/redis_dts.tar.gz"
old_dts_pkg="$dts_parent_dir/redis_dts.tar.gz"

conf_template_file="$dts_server_dir/config-template.yaml"
conf_tmp_file="$dts_server_dir/tmp_config.yaml"
conf_prod_file="$dts_server_dir/config.yaml"

# 下面函数中 0 表示成功,1 表示失败
function is_dts_server_alive() {
    processCnt=$(ps -ef|grep $dts_server_tool|grep -ivE "grep|redis-sync|redis-shake|dbactuator"|wc -l)
    if [[ $processCnt -gt 0 ]]
    then
        echo "dts server alive"
        return 0
    else
        echo "dts server not alive"
        return 1
    fi
}

function is_dts_server_able_to_stop() {
    other_process=$(ps aux|grep 'redis_dts'|grep -vE 'dbactuator|grep|./redis_dts_server|redis-sync|redis-shake' || true )
    if [[ -n $other_process ]]
    then
        echo "other process is running,cannot stop $dts_server_tool,pls check"
        echo "$other_process"
        return 1
    else
        echo "no other process is running,can stop $dts_server_tool"
        return 0
    fi
}

function stop_dts_server() {
    is_dts_server_alive
    if [[ $? -eq 0 ]]
    then
        is_dts_server_able_to_stop
        if [[ $? -eq 0 ]]
        then
            chown -R $system_user:$system_user $dts_parent_dir
            echo "stop $dts_server_tool"
            su - $system_user -c "cd $dts_server_dir && sh stop.sh"
        else
            echo "stop $dts_server_tool failed"
            exit -1
        fi
    else
        echo "$dts_server_tool not alive"
    fi
}

function start_dts_server() {
    is_dts_server_alive
    if [[ $? -eq 0 ]]
    then
        echo "$dts_server_tool already alive"
    else
        chown -R $system_user:$system_user $dts_parent_dir
        echo "start $dts_server_tool"
        su - $system_user -c "cd $dts_server_dir && sh start.sh"
    fi
}

function get_file_md5(){
    local file=$1
    if [[ -e $file ]]
    then
        md5=$(md5sum $file|awk '{print $1}')
        echo $md5
    else
        echo ""
    fi
}

function generate_tmp_config_file(){

    if [[ ! -e $conf_template_file ]]
    then
        echo "config template file($conf_template_file) not exists"
        exit -1
    fi
    cp $conf_template_file $conf_tmp_file
    sed -i -e "s#VAR_bk_dbm_nginx_url#$bk_dbm_nginx_url#g" $conf_tmp_file
    sed -i -e "s#VAR_bk_dbm_cloud_id#$bk_dbm_cloud_id#g" $conf_tmp_file
    sed -i -e "s#VAR_bk_dbm_cloud_token#$bk_dbm_cloud_token#g" $conf_tmp_file
    sed -i -e "s#VAR_system_user#$system_user#g" $conf_tmp_file
    sed -i -e "s#VAR_system_password#$system_password#g" $conf_tmp_file
    sed -i -e "s#VAR_city_name#$city_name#g" $conf_tmp_file
    sed -i -e "s#VAR_warning_msg_notifiers#$warning_msg_notifiers#g" $conf_tmp_file
    echo "generate tmp config file:$conf_tmp_file success"
}

# 0 表示更新,1 表示未更新
function is_config_file_updated(){
    if [[ -e $conf_template_file ]]
    then
        generate_tmp_config_file
    fi
    if [[ ! -e $conf_prod_file ]]
    then
        echo "config file($conf_prod_file) not exists"
        return 0
    fi

    old_md5=$(get_file_md5 $conf_prod_file)
    new_md5=$(get_file_md5 $conf_tmp_file)

    if [[ $old_md5 == $new_md5 ]]
    then
        echo "config file($conf_tmp_file) not updated"
        return 1
    else
        echo "config file($conf_prod_file) updated"
        return 0
    fi
}

#更新配置文件
function update_config_file(){
    is_config_file_updated
    if [[ $? -eq 0 ]]
    then
        echo "update config file"
        cp $conf_tmp_file $conf_prod_file
    else
        echo "config file($conf_tmp_file) not updated"
    fi
}

# 0 表示更新，-1 表示未更新
function is_dts_pkg_updated(){
    if [[ ! -e $dts_server_dir ]]
    then
        echo "dts server dir($dts_server_dir) not exists"
        return 0
    fi
    if [[ ! -e $old_dts_pkg ]]
    then
        echo "old dts pkg not exists"
        return 0
    fi

    if [[ ! -e $new_dts_pkg ]]
    then
        echo "new dts pkg($new_dts_pkg) not exists"
        exit -1
    fi

    old_md5=$(get_file_md5 $old_dts_pkg)
    new_md5=$(get_file_md5 $new_dts_pkg)

    if [[ $old_md5 == $new_md5 ]]
    then
        echo "dts pkg($new_dts_pkg) not updated"
        return 1
    else
        echo "dts pkg($old_dts_pkg) updated"
        return 0
    fi
}

#更新dts包
function update_dts_pkg(){
    is_dts_pkg_updated
    if [[ $? -eq 0 ]]
    then
        echo "update dts pkg"
        cp $new_dts_pkg $old_dts_pkg
        cd $dts_parent_dir
        tar -zxvf $old_dts_pkg
    else
        echo "dts pkg($new_dts_pkg) not updated"
    fi
}

# dir 不存在则创建
if [[ ! -d $dts_parent_dir ]]
then
    mkdir -p $dts_parent_dir
fi

is_dts_pkg_updated
dts_pkg_updated=$?
is_config_file_updated
conf_file_updated=$?

#如果dts包或者配置文件都没更新,则不需要重启dts server
if [[ $dts_pkg_updated -eq 1 && $conf_file_updated -eq 1 ]]
then
    echo "dts pkg($new_dts_pkg) and config file($conf_prod_file) not updated"
    is_dts_server_alive
    dts_alive=$?
    if [[ $dts_alive -eq 0 ]]
    then
        echo "dts server alive,do nothing"
    fi
fi
echo "dts pkg($new_dts_pkg) or config file($conf_prod_file) updated"
stop_dts_server
update_dts_pkg
update_config_file
start_dts_server
sleep 1
is_dts_server_alive
if [[ $? -eq 0 ]]
then
    echo "update dts server success"
else
    echo "update dts server failed,dts_server not alive"
    exit -1
fi
"""

stop_redis_dts_server_template = """
dns_servers="{{dns_servers}}"

while read -r line
do
    # skip empty line
    if [[ "$line" =~ ^[[:space:]]*$ ]]; then
        continue
    fi
    sed -i "/$line/d" /etc/resolv.conf
done <<< "$dns_servers"

dts_server_tool="redis_dts_server"

dts_parent_dir="$REDIS_DATA_DIR/dbbak"
dts_server_dir="$dts_parent_dir/redis_dts"

new_dts_pkg="/data/install/redis_dts.tar.gz"
old_dts_pkg="$dts_parent_dir/redis_dts.tar.gz"

conf_template_file="$dts_server_dir/config-template.yaml"
conf_tmp_file="$dts_server_dir/tmp_config.yaml"
conf_prod_file="$dts_server_dir/config.yaml"

# 下面函数中 0 表示成功,1 表示失败
function is_dts_server_alive() {
    processCnt=$(ps -ef|grep $dts_server_tool|grep -ivE "grep|redis-sync|redis-shake|dbactuator"|wc -l)
    if [[ $processCnt -gt 0 ]]
    then
        echo "dts server alive"
        return 0
    else
        echo "dts server not alive"
        return 1
    fi
}

function is_dts_server_able_to_stop() {
    other_process=$(ps aux|grep 'redis_dts'|grep -vE 'dbactuator|grep|./redis_dts_server|redis-sync|redis-shake' || true )
    if [[ -n $other_process ]]
    then
        echo "other process is running,cannot stop $dts_server_tool,pls check"
        echo "$other_process"
        return 1
    else
        echo "no other process is running,can stop $dts_server_tool"
        return 0
    fi
}

function stop_dts_server() {
    is_dts_server_alive
    if [[ $? -eq 0 ]]
    then
        is_dts_server_able_to_stop
        if [[ $? -eq 0 ]]
        then
            chown -R $system_user:$system_user $dts_parent_dir
            echo "stop $dts_server_tool"
            su - $system_user -c "cd $dts_server_dir && sh stop.sh"
        else
            echo "stop $dts_server_tool failed.There are some tasks running,pls check"
            exit -1
        fi
    else
        echo "$dts_server_tool not alive"
    fi
}

# 如果 dts server 还在运行,则判断能否停止,如果能停止,则停止,否则退出
stop_dts_server

# 如果 prod config 文件存在,则删除
if [[ -e $conf_prod_file ]]
then
    echo "rm -f $conf_prod_file"
    rm -f $conf_prod_file
fi
"""
