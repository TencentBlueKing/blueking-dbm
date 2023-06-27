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


class DtsCopyType(str, StructuredEnum):
    """DTS 数据复制 类型"""

    REDIS_CLUSTER_SHARD_NUM_UPDATE = EnumField("REDIS_CLUSTER_SHARD_NUM_UPDATE", _("redis集群分片数变更"))
    REDIS_CLUSTER_TYPE_UPDATE = EnumField("REDIS_CLUSTER_TYPE_UPDATE", _("redis集群类型变更"))
    REDIS_CLUSTER_DATA_COPY = EnumField("REDIS_CLUSTER_DATA_COPY", _("redis集群数据复制"))

    ONE_APP_DIFF_CLUSTER = EnumField("one_app_diff_cluster", _("同一业务不同集群"))
    DIFF_APP_DIFF_CLUSTER = EnumField("diff_app_diff_cluster", _("不同业务不同集群"))
    COPY_TO_OTHER_SYSTEM = EnumField("copy_to_other_system", _("复制到其他系统"))
    COPY_FROM_ROLLBACK_INSTANCE = EnumField("copy_from_rollback_instance", _("从回档实例复制数据"))
    USER_BUILT_TO_DBM = EnumField("user_built_to_dbm", _("用户自建redis迁移到DBM"))


class DTS_ONLINE_SWITCH_TYPE(str, StructuredEnum):
    """DTS在线切换类型"""

    AUTO = EnumField("auto", _("自动切换"))
    USER_CONFIRM = EnumField("user_confirm", _("用户确认切换"))


class DtsCommonsVarS(str, StructuredEnum):
    """DTS公共变量"""

    # 数据修复模式
    AUTO_REPAIR = EnumField("auto_repair", _("自动修复"))
    MANUAL_CONFIRM = EnumField("manual_confirm", _("用户确认"))

    AUTO_EXECUTION = EnumField("auto_execution", _("自动执行"))
    SCHEDULED_EXECUTION = EnumField("scheduled_execution", _("定时执行"))

    AUTO_DISCONNECT_AFTER_REPLICATION = EnumField("auto_disconnect_after_replication", _("复制完成后自动断开同步关系"))
    KEEP_SYNC_WITH_REMINDER = EnumField("keep_sync_with_reminder", _("复制完成后保持同步关系，定时发送断开同步提醒"))

    # 校验修复类型
    DATA_CHECK_AND_REPAIR = EnumField("data_check_and_repair", _("数据校验并修复"))
    DATA_CHECK_ONLY = EnumField("data_check_only", _("仅进行数据校验，不进行修复"))
    NO_CHECK_NO_REPAIR = EnumField("no_check_no_repair", _("不校验不修复"))

    # 频率
    ONCE_AFTER_REPLICATION = EnumField("once_after_replication", _("复制完成后执行一次"))
    ONCE_DAILY = EnumField("once_daily", _("每天一次"))
    ONCE_EVERY_THREE_DAYS = EnumField("once_every_three_days", _("每三天一次"))
    ONCE_WEEKLY = EnumField("once_weekly", _("每周一次"))

    # 写入模式
    DELETE_AND_WRITE_TO_REDIS = EnumField(
        "delete_and_write_to_redis", _("先删除同名redis key, 再执行写入 (如: del $key + hset $key)")
    )
    KEEP_AND_APPEND_TO_REDIS = EnumField("keep_and_append_to_redis", _("保留同名redis key, 追加写入 (如: hset $key)"))
    FLUSHALL_AND_WRITE_TO_REDIS = EnumField("flushall_and_write_to_redis", _("先清空目标集群所有数据,在写入"))


class TimeoutVars(str, StructuredEnum):
    """
    超时时间
    """

    NEVER = EnumField("never", _("永不超时"))
    ONE_HOUR = EnumField("1hour", _("1小时"))
    THREE_HOURS = EnumField("3hours", _("3小时"))
    SIX_HOURS = EnumField("6hours", _("6小时"))
    ONE_DAY = EnumField("1day", _("1天"))
    TWO_DAYS = EnumField("2days", _("2天"))
    ONE_WEEK = EnumField("1week", _("1周"))


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
