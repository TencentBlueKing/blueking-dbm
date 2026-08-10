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
from datetime import datetime

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_report.mysql_backup.handers import MySQLBackupHandler
from backend.dbm_aiagent.mcp_tools.exceptions import (
    DBMMcpBackupNotFoundException,
    DBMMcpNotSupportClusterTypeException,
)
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ

BYTES_PER_GB = 1024 * 1024 * 1024

DEFAULT_BACKUP_METHODS = ["full_by_ticket", "full_by_regular", "partial_by_ticket"]


def query_backup_logs(
    bk_biz_id: int,
    cluster_domain: str,
    backup_id: str,
    rollback_time: datetime,
    start_time: datetime,
    end_time: datetime,
) -> list[dict]:
    """
    根据时间范围查询集群的备份记录
    @param bk_biz_id: 业务 ID
    @param cluster_domain: 集群域名
    @param backup_id: 备份 ID
    @param rollback_time: 回滚时间
    @param start_time: 查询开始时间
    @param end_time: 查询结束时间
    """
    cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    if cluster_obj.cluster_type in [ClusterType.TenDBSingle, ClusterType.TenDBHA, ClusterType.TenDBCluster]:
        backup_infos = query_backup_log(
            cluster_id=cluster_obj.id,
            cluster_type=cluster_obj.cluster_type,
            backup_id=backup_id,
            rollback_time=rollback_time,
            start_time=start_time,
            end_time=end_time,
        )
        return [_extract_backup_info(info) for info in backup_infos]
    else:
        raise DBMMcpNotSupportClusterTypeException(cluster_type=cluster_obj.cluster_type)


def query_backup_log(
    cluster_id: int,
    cluster_type: str,
    backup_id: str = None,
    rollback_time: datetime = None,
    start_time: datetime = None,
    end_time: datetime = None,
) -> list[dict]:
    """获取备份信息"""
    if backup_id:
        return [get_backup_info_from_backup_id(cluster_id=cluster_id, cluster_type=cluster_type, backup_id=backup_id)]
    elif rollback_time:
        return [get_latest_backup_info(cluster_id=cluster_id, cluster_type=cluster_type, latest_time=rollback_time)]
    else:
        return get_backup_info_list(
            cluster_id=cluster_id, cluster_type=cluster_type, start_time=start_time, end_time=end_time
        )


def get_backup_info_from_backup_id(cluster_id: int, cluster_type: str, backup_id: str) -> dict:
    """根据backup_id获取备份信息"""
    handler = MySQLBackupHandler(cluster_id=cluster_id, backup_method=DEFAULT_BACKUP_METHODS, backup_id=backup_id)
    if cluster_type in [ClusterType.TenDBSingle, ClusterType.TenDBHA]:
        backup_info = handler.get_tendbha_rollback_backup_info()
        if backup_info:
            backup_info = backup_info[0]
    elif cluster_type == ClusterType.TenDBCluster:
        backup_info = handler.get_spider_rollback_backup_info(limit_one=True)
    else:
        raise DBMMcpNotSupportClusterTypeException(cluster_type=cluster_type)
    if not backup_info:
        raise DBMMcpBackupNotFoundException(
            msg=_("cluster_id: {} cluster_type: {} backup_id: {}").format(cluster_id, cluster_type, backup_id)
        )
    return backup_info


def get_latest_backup_info(cluster_id: int, cluster_type: str, latest_time: datetime = None) -> dict:
    """根据latest_time获取最新备份信息"""
    handler = MySQLBackupHandler(cluster_id=cluster_id, backup_method=DEFAULT_BACKUP_METHODS)
    if cluster_type in [ClusterType.TenDBSingle, ClusterType.TenDBHA]:
        backup_info = handler.get_tendb_latest_backup_info(latest_time)
    elif cluster_type == ClusterType.TenDBCluster:
        backup_info = handler.get_spider_rollback_backup_info(latest_time, limit_one=True)
    else:
        raise DBMMcpNotSupportClusterTypeException(cluster_type=cluster_type)
    if not backup_info:
        raise DBMMcpBackupNotFoundException(
            msg=_("cluster_id: {} cluster_type: {} latest_time: {}").format(cluster_id, cluster_type, latest_time)
        )
    return backup_info


def get_backup_info_list(
    cluster_id: int, cluster_type: str, start_time: datetime = None, end_time: datetime = None
) -> list[dict]:
    """
    获取备份信息列表
    仅最近{BACKUP_FILE_DEADLINE_DAYS}天的备份记录可以查询，如果用户指定了时间范围，查询指定时间范围内的备份记录
    """
    handler = MySQLBackupHandler(cluster_id=cluster_id, backup_method=DEFAULT_BACKUP_METHODS)
    if cluster_type in [ClusterType.TenDBSingle, ClusterType.TenDBHA]:
        backup_infos = handler.get_tendbha_rollback_backup_info(latest_time=end_time, start_time=start_time)
    elif cluster_type == ClusterType.TenDBCluster:
        spider_backup = handler.get_spider_rollback_backup_info(latest_time=end_time, start_time=start_time)
        backup_infos = list(spider_backup.values()) if spider_backup else []
    else:
        raise DBMMcpNotSupportClusterTypeException(cluster_type=cluster_type)
    if not backup_infos:
        raise DBMMcpBackupNotFoundException(
            msg=_("cluster_id: {} cluster_type: {} start_time: {} end_time: {}").format(
                cluster_id, cluster_type, start_time, end_time
            )
        )
    return backup_infos


def _extract_backup_info(info: dict) -> dict:
    """提取关键字段"""
    return {
        "backup_consistent_time": info.get("backup_consistent_time"),
        "backup_id": info.get("backup_id"),
        "backup_type": info.get("backup_type"),
        "backup_method": info.get("backup_method"),
        "backup_tool": info.get("backup_tool"),
        "total_filesize_gb": round((info.get("total_filesize") or 0) / BYTES_PER_GB, 2),
        "bill_id": info.get("bill_id"),
    }
