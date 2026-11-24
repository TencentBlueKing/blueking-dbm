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
from typing import Dict, List, Tuple

from backend.components import DRSApi
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.flow.utils.mysql.cluster_variables.collector import (
    DEFAULT_RPC_BATCH_SIZE,
    ClusterVariableQueryError,
    collect_cluster_runtime_variables,
    query_variables_for_addresses,
)

# 目录/路径/文件类变量名后缀(小写匹配), 这类配置不属于核心运行参数, 过滤掉
_PATH_LIKE_NAME_SUFFIXES = ("dir", "_file", "_path", "_home")
# 目录/路径/文件类变量名关键字(小写匹配)
_PATH_LIKE_NAME_KEYWORDS = ("socket", "secure_file_priv", "log_error", "character_sets_dir")

# MyISAM 引擎相关变量名前缀(小写匹配); 如 myisam_sort_buffer_size、myisam_mmap_size 等, 业务巡检极少使用, 默认不输出
_MYISAM_VARIABLE_PREFIX = "myisam_"
# Performance Schema 消费者类变量名前缀(小写匹配); 过滤 performance_schema_* 子项
_PERFORMANCE_SCHEMA_VARIABLE_PREFIX = "performance_schema_"
# SSL 相关变量名前缀(小写匹配); 巡检对比价值低, 默认不输出
_SSL_VARIABLE_PREFIX = "ssl_"
# report_* 实例上报相关变量名前缀(小写匹配); 如 report_host/report_port, 巡检对比价值低
_REPORT_VARIABLE_PREFIX = "report_"

# InnoDB 低价值前缀(小写匹配); 全文/API/monitor/buffer pool 热启停等, 配置巡检极少使用
_LOW_VALUE_INNODB_PREFIXES = (
    "innodb_ft_",
    "innodb_api_",
    "innodb_monitor_",
    "innodb_buffer_pool_dump_",
    "innodb_buffer_pool_load_",
)
# InnoDB 低价值精确键(小写匹配)
_LOW_VALUE_INNODB_KEYS = frozenset(
    {
        "innodb_version",
        "innodb_buffer_pool_filename",
        "innodb_file_format_check",
        "innodb_file_format_max",
        "innodb_support_xa",
    }
)

# Spider 接入层无关前缀(小写 startswith); 存储/复制向参数对 Spider 无分析价值
_SPIDER_IGNORED_VARIABLE_PREFIXES = (
    "innodb_",
    "slave_",
    "relay_log",
    "replicate_",
    "rpl_semi_sync",
    "optimizer_switch",
    "version_comment",
    "local_infile",
)

# 实例级/环境相关变量, 巡检对比价值低, 不输出
IGNORED_RUNTIME_VARIABLE_KEYS = [
    "expire_logs_days",
    "read_only",
    "super_read_only",
    "server_id",
    "sync_binlog",
    "performance_schema",
    "tls_version",
    "bind_address",
    "hostname",
    "local_infile",
]


def _is_path_like_variable(name: str, value: str) -> bool:
    """判断变量是否为目录/路径/文件类配置(需被过滤)。"""
    lname = name.lower()
    if lname.endswith(_PATH_LIKE_NAME_SUFFIXES):
        return True
    if any(keyword in lname for keyword in _PATH_LIKE_NAME_KEYWORDS):
        return True
    if value and value.startswith("/"):
        return True
    return False


def _is_low_value_innodb_variable(lname: str) -> bool:
    """判断是否为 InnoDB 低价值变量(全文/API/monitor/热启停/过时键等)。"""
    if lname in _LOW_VALUE_INNODB_KEYS:
        return True
    return any(lname.startswith(prefix) for prefix in _LOW_VALUE_INNODB_PREFIXES)


def _filter_variables(table_data: List[Dict]) -> Dict[str, str]:
    """黑名单过滤: 去除目录/路径类、ssl_、report_、MyISAM、performance_schema_*、InnoDB 低价值项与 IGNORED_RUNTIME_VARIABLE_KEYS。"""
    variables = {}
    for row in table_data:
        name = row.get("Variable_name", "")
        value = row.get("Value", "")
        if not name:
            continue
        lname = name.lower()
        if lname in IGNORED_RUNTIME_VARIABLE_KEYS:
            continue
        if lname.startswith(_SSL_VARIABLE_PREFIX):
            continue
        if lname.startswith(_REPORT_VARIABLE_PREFIX):
            continue
        if lname.startswith(_MYISAM_VARIABLE_PREFIX):
            continue
        if lname.startswith(_PERFORMANCE_SCHEMA_VARIABLE_PREFIX):
            continue
        if _is_low_value_innodb_variable(lname):
            continue
        if _is_path_like_variable(name, value):
            continue
        variables[name] = value
    return variables


def _apply_spider_variable_filter(variables: Dict[str, str]) -> Dict[str, str]:
    """Spider 角色裁撤存储/复制向参数。"""
    filtered = {}
    for name, value in (variables or {}).items():
        lname = name.lower()
        if any(lname.startswith(prefix) for prefix in _SPIDER_IGNORED_VARIABLE_PREFIXES):
            continue
        filtered[name] = value
    return filtered


def _apply_storage_engine_filter(variables: Dict[str, str]) -> Dict[str, str]:
    """存储层按 default_storage_engine 裁撤: 非 InnoDB 时去掉全部 innodb_*。

    引擎键缺失或为空时保守不裁整段 innodb_*。
    """
    if not variables:
        return {}
    engine = (variables.get("default_storage_engine") or "").strip().lower()
    if not engine or engine == "innodb":
        return dict(variables)
    return {name: value for name, value in variables.items() if not name.lower().startswith("innodb_")}


def _query_variables_for_addresses(
    bk_cloud_id: int,
    addresses: List[str],
) -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, str]]]:
    """批量执行 SHOW GLOBAL VARIABLES, 返回 (过滤后变量表, 各地址 datadir 衍生字段)。"""
    try:
        addr_to_variables, addr_to_datadir_meta, unused_errors = query_variables_for_addresses(
            bk_cloud_id=bk_cloud_id,
            addresses=addresses,
            fail_fast=True,
            variable_filter=_filter_variables,
            extract_datadir=True,
            rpc_func=DRSApi.v2_mysql_rpc,
            batch_size=DEFAULT_RPC_BATCH_SIZE,
        )
    except ClusterVariableQueryError as exc:
        raise DBMMcpBaseException(msg=str(exc)) from exc
    return addr_to_variables, addr_to_datadir_meta


def cluster_runtime_variables(cluster_obj: Cluster) -> Dict:
    """查询集群所有角色实例的运行时核心配置, 带版本信息; 另返回 datadir 及推导的 data_dir_mount。

    已过滤目录/路径类、ssl_*、report_*、myisam_*、performance_schema_*、InnoDB 低价值项与 IGNORED_RUNTIME_VARIABLE_KEYS；
    Spider 另裁存储/复制向前缀；存储层非 InnoDB 时裁全部 innodb_*。
    """
    try:
        return collect_cluster_runtime_variables(
            cluster_obj=cluster_obj,
            db_alias=MYSQL_MCP_DB_READ,
            fail_fast=True,
            variable_filter=_filter_variables,
            storage_filter=_apply_storage_engine_filter,
            spider_filter=_apply_spider_variable_filter,
            extract_datadir=True,
            rpc_func=DRSApi.v2_mysql_rpc,
        )
    except ClusterVariableQueryError as exc:
        raise DBMMcpBaseException(msg=str(exc)) from exc
