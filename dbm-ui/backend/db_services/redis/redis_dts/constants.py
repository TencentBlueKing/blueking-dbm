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
from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import ugettext_lazy as _


class DtsTaskType(str, StructuredEnum):
    """DTS task类型枚举"""

    # tendis ssd相关任务
    TENDISSSD_BACKUP = EnumField("tendisBackup", _("tendis ssd备份任务"))
    TENDISSSD_BACKUPFILE_FETCH = EnumField("backupfileFetch", _("tendis ssd备份拉取任务"))
    TENDISSSD_TREDISDUMP = EnumField("tendisdump", _("tendis ssd备份解析任务"))
    TENDISSSD_CMDSIMPOTER = EnumField("cmdsImpoter", _("tendis ssd数据导入任务"))
    TENDISSSD_MAKESYNC = EnumField("makeSync", _("tendis ssd拉起sync任务"))
    TENDISSSD_WATCHOLDSYNC = EnumField("WatchOldSync", _("tendis ssd监视sync任务"))

    # redis cache相关任务
    MAKE_CACHE_SYNC = EnumField("makeCacheSync", _("redis cache拉起redis-shake任务"))
    WATCH_CACHE_SYNC = EnumField("watchCacheSync", _("tendis ssd监视sync任务"))

    # tendisplus相关任务
    TENDISPLUS_MAKESYNC = EnumField("tendisplusMakeSync", _("tendisplus拉起reids-sync任务"))
    # 将全量数据同步 与 增量数据同步分开,原因是 存量数据同步讲占用较多内存,增量不占用内存
    TENDISPLUS_SENDBULK = EnumField("tendisplusSendBulk", _("tendisplus全量数据同步"))
    TENDISPLUS_SENDINCR = EnumField("tendisplusSendIncr", _("tendisplus增量数据同步"))


class DtsOperateType(str, StructuredEnum):
    """DTS task操作类型枚举"""

    SYNC_STOP_TODO = EnumField("SyncStopTodo", _("停止数据同步todo"))
    SYNC_STOP_FAIL = EnumField("SyncStopFail", _("停止数据同步失败"))
    SYNC_STOP_SUCC = EnumField("SyncStopSucc", _("停止数据同步成功"))

    FORCE_KILL_TODO = EnumField("ForceKillTaskTodo", _("强制暂停任务todo"))
    FORCE_KILL_FAIL = EnumField("ForceKillTaskFail", _("强制暂停任务失败"))
    FORCE_KILL_SUCC = EnumField("ForceKillTaskSucc", _("强制暂停任务成功"))


# DTS在线切换twemproxy前置检查脚本
DTS_SWITCH_TWEMPROXY_PRECHECK = """
srcProxyIP={{SRC_PROXY_IP}}
srcProxyPort={{SRC_PROXY_PORT}}
srcAdminPort=$(($srcProxyPort+1000))
srcProxyPassword="{{SRC_PROXY_PASSWORD}}"

filterRet=$(ifconfig|grep $srcProxyIP)
if [[ -z $filterRet ]]
then
echo "[ERROR] 'ifconfig' not found $srcProxyIP"
exit -1
fi

confFile=$(ps aux|grep "nutcracker.$srcProxyPort.yml"|grep -v grep|grep --only-match -P 'c .*.yml '|awk '{print $2}')
if [[ -z $confFile ]]
then
echo "[ERROR] get twemproxy $srcProxyPort conf file fail"
exit -1
fi

filterRet=$(grep -iw 'listen' $confFile|grep "$srcProxyIP:$srcProxyPort")
if [[ -z $filterRet ]]
then
echo "[ERROR] $srcProxyIP twemproxy confFile:$confFile listen not $srcProxyIP:$srcProxyPort"
exit -1
fi

filterRet=$(grep -iw 'password' $confFile|grep "$srcProxyPassword")
if [[ -z $filterRet ]]
then
echo "[ERROR] $srcProxyIP twemproxy confFile:$confFile password not $srcProxyPassword"
exit -1
fi

filterRet=$(echo 'get nosqlproxy servers'| /home/mysql/dbtools/netcat  $srcProxyIP  $srcAdminPort)
if [[ -z $filterRet ]]
then
echo "[ERROR] twemproxy[$srcProxyIP:$srcAdminPort] get backend redis fail"
exit -1
fi

confDir=$(dirname $confFile)
ret=$(sed -n '{H;s/$/\\\\n/;p;g;}' $confFile > $confDir/dts_proxy_tmp.txt && tr -d '\n' < $confDir/dts_proxy_tmp.txt | cat)
echo "<ctx>{\\\"data\\\":\\\"${ret}\\\"}</ctx>"
"""

# DTS在线切换predixy前置检查脚本
DTS_SWITCH_PREDIXY_PRECHECK = """
srcProxyIP={{SRC_PROXY_IP}}
srcProxyPort={{SRC_PROXY_PORT}}
srcAdminPort=$(($srcProxyPort+1000))
srcProxyPassword="{{SRC_PROXY_PASSWORD}}"

filterRet=$(ifconfig|grep $srcProxyIP)
if [[ -z $filterRet ]]
then
echo "[ERROR] 'ifconfig' not found $srcProxyIP"
exit -1
fi

confFile=$(ps aux|grep "/usr/local/predixy/bin/predixy"|grep -v grep|awk '{print $NF}')
if [[ -z $confFile ]]
then
echo "[ERROR] get predixy $srcProxyPort conf file fail"
exit -1
fi

filterRet=$(grep -iw 'Bind' $confFile|grep "$srcProxyIP:$srcProxyPort")
if [[ -z $filterRet ]]
then
echo "[ERROR] $srcProxyIP predixy confFile:$confFile Bind not $srcProxyIP:$srcProxyPort"
exit -1
fi

filterRet=$(grep -iw 'Auth' $confFile|grep "$srcProxyPassword")
if [[ -z $filterRet ]]
then
echo "[ERROR] $srcProxyIP predixy confFile:$confFile password not $srcProxyPassword"
exit -1
fi

getVal=$(/usr/local/predixy/bin/redis-cli -h $srcProxyIP -p $srcProxyPort -a $srcProxyPassword get a)
shopt -s nocasematch;
if [[ $getVal =~ "ERR" ]]
then
echo "[ERROR] predixy($srcProxyIP:$srcProxyPort) get a failed,err:$getVal"
exit -1
fi

python -c "import json; conf_data=open('$confFile').read(); json_data={'data':conf_data}; \
s1='<ctx>'+json.dumps(json_data)+'</ctx>';print(s1)"
"""

# 添加/etc/hosts
SERVERS_ADD_ETC_HOSTS = """
lines="{}"

while read -r line
do
    # skip empty line
    if [[ "$line" =~ ^[[:space:]]*$ ]]; then
        continue
    fi
    domain=$(cut -d' ' -f2 <<< "$line")
    sed -i "/$domain/d" /etc/hosts
    if ! grep -qF "$line" /etc/hosts; then
        echo "$line" | tee -a /etc/hosts >/dev/null
        echo "Added: $line"
    else
        echo "Skipped: $line"
    fi
done <<< "$lines"
"""

# 删除/etc/hosts
SERVERS_DEL_ETC_HOSTS = """
lines="{}"

while read -r line
do
    # skip empty line
    if [[ "$line" =~ ^[[:space:]]*$ ]]; then
        continue
    fi
    sed -i "/$line/d" /etc/hosts
    echo "Deleted: $line"
done <<< "$lines"

"""
