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
from backend.db_services.ipchooser.constants import DB_MANAGE_SET
from backend.db_services.redis.rollback.exceptions import RollbackPlanError
from backend.flow.consts import DEFAULT_TWEMPROXY_SEG_MIN_NUM, DEFAULT_TWEMPROXY_SEG_TOTOL_NUM

RESOURCE_TAG = "db_services/redis/rollback"

# 查询某个特定时间点附近的日志时，默认在3天内
BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS = 3
# 查询同一批次备份，默认是三小时内
BACKUP_LOG_ROLLBACK_TIME_RANGE_HOURS = 3

# Batch list query window. Large clusters (e.g. 180 shards) produce thousands of file records;
# capping the window at 30 days protects backend query and frontend rendering performance.
BACKUP_BATCH_DEFAULT_WINDOW_DAYS = 7
BACKUP_BATCH_MAX_WINDOW_DAYS = 30

BACKUP_STATUS_SUCCESS = "to_backup_system_success"
# Role at backup time, as dbmon reports it and writes it into file names.
BACKUP_ROLE_MASTER = "master"
BACKUP_ROLE_SLAVE = "slave"
SWITCHED_SHARD_VALUE = "switched-0"
SINGLE_INSTANCE_SHARD_VALUE = "{}-{}".format(DEFAULT_TWEMPROXY_SEG_MIN_NUM, DEFAULT_TWEMPROXY_SEG_TOTOL_NUM - 1)

TWEMPROXY_SHARD_TOTAL = DEFAULT_TWEMPROXY_SEG_TOTOL_NUM
TWEMPROXY_SHARD_MIN = DEFAULT_TWEMPROXY_SEG_MIN_NUM

CACHE_CLUSTER_TYPES = (
    ClusterType.TendisTwemproxyRedisInstance.value,
    ClusterType.TendisRedisInstance.value,
)
SSD_CLUSTER_TYPES = (
    ClusterType.TwemproxyTendisSSDInstance.value,
    ClusterType.TendisTendisSSDInstance.value,
)
# Tendisplus engine: restorebackup and per-kvstore binlogs, whether or not cluster-enabled.
TENDISPLUS_TYPES = (ClusterType.TendisPredixyTendisplusCluster.value,)
REDIS_CLUSTER_TYPES = (ClusterType.TendisPredixyRedisCluster.value,)
# Temp clusters of these types are formed after restore and must hold every slot.
CLUSTER_PROTOCOL_TYPES = (
    ClusterType.TendisPredixyTendisplusCluster.value,
    ClusterType.TendisPredixyRedisCluster.value,
)
# Data loaded into memory, so the busiest host must fit it.
IN_MEMORY_CLUSTER_TYPES = CACHE_CLUSTER_TYPES + REDIS_CLUSTER_TYPES
BINLOG_CLUSTER_TYPES = SSD_CLUSTER_TYPES + TENDISPLUS_TYPES
ROLLBACK_CLUSTER_TYPES = CACHE_CLUSTER_TYPES + SSD_CLUSTER_TYPES + CLUSTER_PROTOCOL_TYPES

CLUSTER_SLOT_TOTAL = 16384

# Binlogs rotate about every 20 minutes but an upload may lag by up to 2 hours, so the lookup
# window is widened on both sides to be sure it holds the files around each end of the chain.
BINLOG_LOOKUP_MARGIN_HOURS = 6

# BKLog window for one batch: from the hour stamped in its identify.
BACKUP_IDENTIFY_WINDOW_DAYS = 1

SHARD_ROUTE_MAX_KEYS = 50
SHARD_ROUTE_CONCURRENCY = 8
# Shards whose binlogs are looked up at once; each costs a report_db query and a BKLog search.
BINLOG_LOCATE_CONCURRENCY = 4

# Task ids per download bill. This is a scheduling granularity, not a backup system limit:
# MySQL rollback already submits up to 500 task ids per bill through the same backupapi/recover.
# Small bills release the shared window sooner and let hosts interleave; 2000 files = 40 calls.
DOWNLOAD_BATCH_SIZE = 50

# One rollback plan keeps at most this many task ids in flight across every target host.
# The backup system sustains about 5000 concurrent downloads shared with every other ticket;
# 100 per plan (two bills of DOWNLOAD_BATCH_SIZE) keeps one rollback well inside that.
# The window and its batch ledger are persisted on the plan row
# (TbTendisRollbackPlan.download_state, see download_window.py).
DOWNLOAD_INFLIGHT_TASK_LIMIT = 100

# The backup system loses some bills: get_recover_result then answers HTTP 500 with
# {"code": 13, "message": "fail,can not find this file"} and the bill never reports again.
# That body only reaches us inside the ApiRequestError message, so a bill counts as lost only
# when every pattern matches it; anything else (timeouts, other 5xx) stays "unknown".
DOWNLOAD_BILL_LOST_PATTERNS = (r"get_recover_result", r'"code"\s*:\s*13\b', r"can not find this file")
# Automatic resubmissions of one batch after its bill was lost; one more loss fails the node.
DOWNLOAD_LOST_RESUBMIT_LIMIT = 2

# rollback_version: datastructure = v1 construction flow, rollback = v2 implementation
DATASTRUCTURE_VERSION = "datastructure"
ROLLBACK_VERSION = "rollback"

# CC topology for temporary rollback hosts: DBM's own manage set, in the cluster's hosting biz.
# The set is never registered in AppMonitorTopo, which is where every metric and log collector
# takes its targets, and clean_cc_topo keeps its empty modules.
ROLLBACK_CC_SET_NAME = DB_MANAGE_SET
ROLLBACK_CC_MODULE_NAME = "redis.rollback"

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

# Conservative unpacked/compressed size ratio for backup files, used by the disk precheck.
UNPACK_RATIO = 3
COMPRESSED_SUFFIXES = (".zst", ".gz", ".lzo")
DISK_USED_RATIO_FAIL = 85
DISK_USED_PLUS_NEED_RATIO_FAIL = 0.9

# Resident memory of a Cache instance per byte of its unpacked data file. Measured RSS / RDB is
# 1.85 on production slaves; AOF is kept separate as it replays commands while loading.
MEMORY_RATIO_RDB = 2.0
MEMORY_RATIO_AOF = 2.0
# Unpacking runs NumCPU / 2 ports at a time, so fewer cores per instance means queueing.
CPU_PER_INSTANCE_HINT = 2

# rocks.write_buffer_size of the Tendisplus temp instances, sent to the actuator as
# write_buffer_mb. Larger buffers flush less often and cut the replay's write amplification
# (S6 bench: 128MB took the restore + replay from 41s to 34s). Every kvstore keeps up to two in
# memory, which the memory precheck counts with the block cache. Compaction and the WAL stay on:
# a failed replay must resume from binlogpos, and the instance must need no settling afterwards.
ROLLBACK_PLUS_WRITE_BUFFER_MB = 128
# Tendisplus keeps up to this many write buffers per kvstore before flushing; the disk precheck
# reserves their worst-case WAL while the replay has the kvstores open.
ROLLBACK_PLUS_MAX_WRITE_BUFFER_NUMBER = 4

# Mirrors of the actuator's rollback limits (dbactuator pkg/rollback): the window it admits
# instances into is MemAvailable less a tenth (memReserveDivisor), and SSD replay streams binlogs
# from the downloaded files without keeping a decompressed or parsed copy on disk.
MEMORY_RESERVE_DIVISOR = 10
