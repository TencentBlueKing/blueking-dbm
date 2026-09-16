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
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_services.redis.rollback.exceptions import RollbackPlanError
from backend.flow.consts import DEFAULT_TWEMPROXY_SEG_MIN_NUM, DEFAULT_TWEMPROXY_SEG_TOTOL_NUM

RESOURCE_TAG = "db_services/redis/rollback"

# 查询某个特定时间点附近的日志时，默认在3天内
BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS = 3
# 查询同一批次备份，默认是三小时内
BACKUP_LOG_ROLLBACK_TIME_RANGE_HOURS = 3

BACKUP_STATUS_SUCCESS = "to_backup_system_success"
SWITCHED_SHARD_VALUE = "switched-0"
SINGLE_INSTANCE_SHARD_VALUE = "{}-{}".format(DEFAULT_TWEMPROXY_SEG_MIN_NUM, DEFAULT_TWEMPROXY_SEG_TOTOL_NUM - 1)

TWEMPROXY_SHARD_TOTAL = DEFAULT_TWEMPROXY_SEG_TOTOL_NUM
TWEMPROXY_SHARD_MIN = DEFAULT_TWEMPROXY_SEG_MIN_NUM

CACHE_CLUSTER_TYPES = (
    ClusterType.TendisTwemproxyRedisInstance.value,
    ClusterType.TendisRedisInstance.value,
)

# rollback_version: datastructure 是旧构造链路(v1)，rollback 是本实现(v2)
DATASTRUCTURE_VERSION = "datastructure"
ROLLBACK_VERSION = "rollback"

# 回档临时实例独立的 CC 模块名，位于 redis 监控 set 下（如 redis.redisserver/rollback），
# 不挂到源集群模块，避免临时实例被当成源集群成员采集
ROLLBACK_CC_MODULE_NAME = "rollback"

SELECT_MODE_BY_TIME = "by_time"
SELECT_MODE_BY_IDENTIFY = "by_identify"
SELECT_MODE_BY_TASK_ID = "by_task_id"


def infer_select_mode(info):
    """Infer select mode from payload fields. Ticket does not send rollback_mode.

    Priority: backup_identify (files optional) > recovery_time_point > backup_task_ids.
    """
    if info.get("backup_identify"):
        return SELECT_MODE_BY_IDENTIFY
    if info.get("recovery_time_point"):
        return SELECT_MODE_BY_TIME
    if info.get("backup_task_ids"):
        return SELECT_MODE_BY_TASK_ID
    raise RollbackPlanError(context={"message": _("必须提供 backup_identify、recovery_time_point 或 backup_task_ids 之一")})


SCOPE_CLUSTER = "cluster"
SCOPE_INSTANCES = "instances"

LOCATOR_SOURCE_TABLE = "table"
LOCATOR_SOURCE_BKLOG = "bklog"

IDENTIFY_PREFIXES = ("SCHEDULED", "REUPLOAD", "FOREVER", "FLUSH", "BILL", "DTS")
IDENTIFY_UNKNOWN = "UNKNOWN"

FILTER_MODE_DELETE_MATCHED = "delete_matched"
FILTER_MODE_KEEP_MATCHED = "keep_matched"

DISK_USED_RATIO_FAIL = 85
DISK_USED_PLUS_NEED_RATIO_FAIL = 0.9
