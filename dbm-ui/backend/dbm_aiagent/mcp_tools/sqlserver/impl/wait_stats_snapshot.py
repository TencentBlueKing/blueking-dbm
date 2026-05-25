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
from typing import Dict, Optional

from backend.components import DRSApi
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.get_instance_address import resolve_sqlserver_addresses

# 等待事件忽略列表：这些等待是 SQL Server 自身后台/空闲行为，无诊断意义
# 参考 SQLSkills 公认的"良性等待"清单，按需扩展
_BENIGN_WAIT_TYPES = (
    "BROKER_EVENTHANDLER",
    "BROKER_RECEIVE_WAITFOR",
    "BROKER_TASK_STOP",
    "BROKER_TO_FLUSH",
    "BROKER_TRANSMITTER",
    "CHECKPOINT_QUEUE",
    "CHKPT",
    "CLR_AUTO_EVENT",
    "CLR_MANUAL_EVENT",
    "CLR_SEMAPHORE",
    "DBMIRROR_DBM_EVENT",
    "DBMIRROR_EVENTS_QUEUE",
    "DBMIRROR_WORKER_QUEUE",
    "DBMIRRORING_CMD",
    "DIRTY_PAGE_POLL",
    "DISPATCHER_QUEUE_SEMAPHORE",
    "EXECSYNC",
    "FSAGENT",
    "FT_IFTS_SCHEDULER_IDLE_WAIT",
    "FT_IFTSHC_MUTEX",
    "HADR_CLUSAPI_CALL",
    "HADR_FILESTREAM_IOMGR_IOCOMPLETION",
    "HADR_LOGCAPTURE_WAIT",
    "HADR_NOTIFICATION_DEQUEUE",
    "HADR_TIMER_TASK",
    "HADR_WORK_QUEUE",
    "KSOURCE_WAKEUP",
    "LAZYWRITER_SLEEP",
    "LOGMGR_QUEUE",
    "ONDEMAND_TASK_QUEUE",
    "PWAIT_ALL_COMPONENTS_INITIALIZED",
    "QDS_PERSIST_TASK_MAIN_LOOP_SLEEP",
    "QDS_CLEANUP_STALE_QUERIES_TASK_MAIN_LOOP_SLEEP",
    "REQUEST_FOR_DEADLOCK_SEARCH",
    "RESOURCE_QUEUE",
    "SERVER_IDLE_CHECK",
    "SLEEP_BPOOL_FLUSH",
    "SLEEP_DBSTARTUP",
    "SLEEP_DCOMSTARTUP",
    "SLEEP_MASTERDBREADY",
    "SLEEP_MASTERMDREADY",
    "SLEEP_MASTERUPGRADED",
    "SLEEP_MSDBSTARTUP",
    "SLEEP_SYSTEMTASK",
    "SLEEP_TASK",
    "SLEEP_TEMPDBSTARTUP",
    "SNI_HTTP_ACCEPT",
    "SP_SERVER_DIAGNOSTICS_SLEEP",
    "SQLTRACE_BUFFER_FLUSH",
    "SQLTRACE_INCREMENTAL_FLUSH_SLEEP",
    "SQLTRACE_WAIT_ENTRIES",
    "WAIT_FOR_RESULTS",
    "WAITFOR",
    "WAITFOR_TASKSHUTDOWN",
    "WAIT_XTP_HOST_WAIT",
    "WAIT_XTP_OFFLINE_CKPT_NEW_LOG",
    "WAIT_XTP_CKPT_CLOSE",
    "XE_DISPATCHER_JOIN",
    "XE_DISPATCHER_WAIT",
    "XE_TIMER_EVENT",
)


def _build_wait_stats_sql(top: int) -> str:
    """构建 wait stats 查询 SQL；忽略良性等待，按总等待时间倒序。"""
    ignore_list = ",".join(f"N'{w}'" for w in _BENIGN_WAIT_TYPES)
    return f"""
SELECT TOP ({top})
    wait_type,
    waiting_tasks_count,
    wait_time_ms,
    max_wait_time_ms,
    signal_wait_time_ms,
    (wait_time_ms - signal_wait_time_ms) AS resource_wait_time_ms,
    CASE WHEN waiting_tasks_count = 0 THEN 0
         ELSE wait_time_ms / waiting_tasks_count END AS avg_wait_time_ms
FROM sys.dm_os_wait_stats
WHERE waiting_tasks_count > 0
  AND wait_type NOT IN ({ignore_list})
ORDER BY wait_time_ms DESC
""".strip()


def sqlserver_wait_stats_snapshot(
    cluster_domain: str,
    address: Optional[str] = None,
    top: int = 15,
) -> Dict:
    """查询实例累计等待统计 TOP N（剔除良性等待）。

    使用通道：sqlserver_sys_read_rpc。

    :param cluster_domain: 集群不可变域名
    :param address: 可选，指定具体实例；不传则缺省查询 master
    :param top: 返回条数
    :return: {
        "cluster_domain": "...",
        "address": "ip:port",
        "role": "...",
        "wait_stats": [...]
    }
    """
    if top <= 0 or top > 100:
        raise DBMMcpBaseException(msg="top must be in (0, 100]")

    bk_cloud_id, instances = resolve_sqlserver_addresses(
        cluster_domain=cluster_domain, address=address, default_role="master"
    )
    target = instances[0]

    rpc_results = DRSApi.sqlserver_sys_read_rpc(
        {
            "bk_cloud_id": bk_cloud_id,
            "addresses": [target["address"]],
            "cmds": [_build_wait_stats_sql(top)],
        }
    )

    rpc_res = rpc_results[0]
    if rpc_res.get("error_msg"):
        raise DBMMcpBaseException(msg=rpc_res["error_msg"])

    cmd_res = rpc_res["cmd_results"][0]
    if cmd_res.get("error_msg"):
        raise DBMMcpBaseException(msg=cmd_res["error_msg"])

    return {
        "cluster_domain": cluster_domain,
        "address": target["address"],
        "role": target["role"],
        "wait_stats": cmd_res.get("table_data") or [],
    }
