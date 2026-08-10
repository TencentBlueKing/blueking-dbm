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
import re
from typing import Tuple

from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.db_meta.models.storage_set_dtl import TenDBClusterStorageSet
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ


def get_cloud_slave_address_and_dbname(
    cluster_type: ClusterType, cluster_domain: str, dbname: str
) -> Tuple[int, str, str]:
    cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).get(immute_domain=cluster_domain, cluster_type=cluster_type)

    if cluster_type == ClusterType.TenDBSingle:
        address = cluster_obj.storageinstance_set.first().ip_port
    elif cluster_type == ClusterType.TenDBHA:
        address = cluster_obj.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.SLAVE).first().ip_port
    else:
        # 取第 0 分片的 slave instance，跟 sanitize_select_sql 里面改写的分片一致
        storage_set = TenDBClusterStorageSet.objects.using(MYSQL_MCP_DB_READ).get(cluster=cluster_obj, shard_id=0)
        one_remote_slave = storage_set.storage_instance_tuple.receiver
        address = one_remote_slave.ip_port

        if dbname:
            dbname = f"{dbname}_0"

    return cluster_obj.bk_cloud_id, address, dbname


# 安全变量名正则：只允许 a-zA-Z_ 字符
_SAFE_NAME_PATTERN = re.compile(r"^[a-zA-Z_]+$")


def safe_sql_in_string(names: list[str]) -> str:
    """将 list[str] 转成安全的 SQL IN 字符串。

    只允许每个元素包含 a-zA-Z_ 字符，否则抛出异常。
    例如: ['wait_timeout', 'version'] -> "('wait_timeout','version')"
    """
    for name in names:
        if not _SAFE_NAME_PATTERN.match(name):
            raise DBMMcpBaseException(msg=f"unsafe variable name: '{name}', only a-zA-Z_ characters are allowed")
    quoted = ",".join(f"'{name}'" for name in names)
    return f"({quoted})"
