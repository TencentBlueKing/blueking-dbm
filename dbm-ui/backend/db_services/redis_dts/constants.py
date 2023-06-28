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
    SYNC_STOP_FAIL = EnumField("SyncStopTodo", _("停止数据同步失败"))
    SYNC_STOP_SUCC = EnumField("SyncStopTodo", _("停止数据同步成功"))

    FORCE_KILL_TODO = EnumField("ForceKillTaskTodo", _("强制暂停任务todo"))
    FORCE_KILL_FAIL = EnumField("ForceKillTaskFail", _("强制暂停任务失败"))
    FORCE_KILL_SUCC = EnumField("ForceKillTaskSucc", _("强制暂停任务成功"))


class DtsBillType(str, StructuredEnum):
    """DTS 单据类型"""

    CLUSTER_NODES_NUM_UPDATE = EnumField("cluster_nodes_num_update", _("集群节点数变更"))
    CLUSTER_TYPE_UPDATE = EnumField("cluster_type_update", _("集群类型变更"))
    CLUSTER_DATA_COPY = EnumField("cluster_data_copy", _("数据复制"))


class DtsCopyType(str, StructuredEnum):
    """DTS 数据复制 类型"""

    ONE_APP_DIFF_CLUSTER = EnumField("one_app_diff_cluster", _("同一业务不同集群"))
    DIFF_APP_DIFF_CLUSTER = EnumField("diff_app_diff_cluster", _("不同业务不同集群"))
    COPY_TO_OTHER_SYSTEM = EnumField("copy_to_other_system", _("复制到其他系统"))
    COPY_FROM_ROLLBACK_TEMP = EnumField("copy_from_rollback_temp", _("从回档临时环境复制数据"))
    USER_BUILT_TO_DBM = EnumField("user_built_to_dbm", _("用户自建redis迁移到DBM"))


class DTS_ONLINE_SWITCH_TYPE(str, StructuredEnum):
    """DTS在线切换类型"""

    AUTO = EnumField("auto", _("自动切换"))
    USER_CONFIRM = EnumField("user_confirm", _("用户确认切换"))


class DTS_DATA_REPAIR_TYPE(str, StructuredEnum):
    """DTS数据修复类型"""

    AUTO = EnumField("auto", _("自动修复"))
    USER_CONFIRM = EnumField("user_confirm", _("用户确认修复"))


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

cat $configFile
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

cat $confFile
"""
