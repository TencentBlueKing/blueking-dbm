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
import logging
import re
from typing import Dict, List, Tuple

from django.core.cache import cache

logger = logging.getLogger("root")

"""MySQL 8.4 复制语法兼容模块

MySQL 8.4 版本移除了旧版 Master/Slave 关键字的兼容，改用 Source/Replica 语法体系。
本模块提供 SQL 命令翻译和返回字段名映射能力，供 _DRSApi.rpc_mysql_replica_compat 调用。

主要功能：
1. 根据实例版本自动翻译旧版复制命令为新版语法
2. 将新版返回字段名映射回旧版字段名，确保上层业务代码无需修改
"""

# 版本缓存配置
_VERSION_CACHE_PREFIX = "drs:mysql_version:"
_VERSION_CACHE_TTL = 60  # 1分钟

# ============================================================
# SQL 命令翻译规则
# 格式：(正则模式, 替换模板, 是否需要对返回结果做字段映射)
# 暂未对 show global variables / show global status 做处理，涉及到输出内容字段的改写
# ============================================================
_CMD_PATTERNS = [
    # show slave status → SHOW REPLICA STATUS（需要字段映射）
    (re.compile(r"(?i)^\s*show\s+slave\s+status\s*;?\s*$"), "SHOW REPLICA STATUS", True),
    # show master status → SHOW BINARY LOG STATUS（需要字段映射）
    (re.compile(r"(?i)^\s*show\s+master\s+status\s*;?\s*$"), "SHOW BINARY LOG STATUS", True),
    # start slave → START REPLICA
    (re.compile(r"(?i)^\s*start\s+slave\b(.*)$"), r"START REPLICA\1", False),
    # stop slave → STOP REPLICA
    (re.compile(r"(?i)^\s*stop\s+slave\b(.*)$"), r"STOP REPLICA\1", False),
    # reset slave [all] → RESET REPLICA [ALL]
    (re.compile(r"(?i)^\s*reset\s+slave\b(.*)$"), r"RESET REPLICA\1", False),
    # reset master → RESET BINARY LOGS AND GTIDS
    (re.compile(r"(?i)^\s*reset\s+master\s*;?\s*$"), "RESET BINARY LOGS AND GTIDS", False),
    # show slave hosts → SHOW REPLICAS
    (re.compile(r"(?i)^\s*show\s+slave\s+hosts\s*;?\s*$"), "SHOW REPLICAS", False),
    # show master logs → SHOW BINARY LOGS
    (re.compile(r"(?i)^\s*show\s+master\s+logs\s*;?\s*$"), "SHOW BINARY LOGS", False),
    # purge master logs → PURGE BINARY LOGS（保留后续条件部分，如 TO 'binlog.000010'）
    (re.compile(r"(?i)^\s*purge\s+master\s+logs\b(.*)$"), r"PURGE BINARY LOGS\1", False),
    # CHANGE MASTER TO → CHANGE REPLICATION SOURCE TO（需要参数名替换，不需要字段映射）
    (re.compile(r"(?i)^\s*CHANGE\s+MASTER\s+TO\b"), "CHANGE REPLICATION SOURCE TO", False),
]

# ============================================================
# CHANGE MASTER TO 参数名替换映射（大小写不敏感匹配）
# ============================================================
_MASTER_PARAM_MAP = {
    "MASTER_HOST": "SOURCE_HOST",
    "MASTER_PORT": "SOURCE_PORT",
    "MASTER_USER": "SOURCE_USER",
    "MASTER_PASSWORD": "SOURCE_PASSWORD",
    "MASTER_LOG_FILE": "SOURCE_LOG_FILE",
    "MASTER_LOG_POS": "SOURCE_LOG_POS",
    "MASTER_AUTO_POSITION": "SOURCE_AUTO_POSITION",
    "MASTER_CONNECT_RETRY": "SOURCE_CONNECT_RETRY",
    "MASTER_RETRY_COUNT": "SOURCE_RETRY_COUNT",
    "MASTER_DELAY": "SOURCE_DELAY",
    "MASTER_HEARTBEAT_PERIOD": "SOURCE_HEARTBEAT_PERIOD",
}

# ============================================================
# SHOW REPLICA STATUS 字段映射（新版字段名 → 旧版字段名）
# ============================================================
_REPLICA_STATUS_FIELD_MAP: Dict[str, str] = {
    "Source_Host": "Master_Host",
    "Source_Port": "Master_Port",
    "Source_User": "Master_User",
    "Replica_IO_Running": "Slave_IO_Running",
    "Replica_SQL_Running": "Slave_SQL_Running",
    "Seconds_Behind_Source": "Seconds_Behind_Master",
    "Source_Log_File": "Master_Log_File",
    "Read_Source_Log_Pos": "Read_Master_Log_Pos",
    "Exec_Source_Log_Pos": "Exec_Master_Log_Pos",
    "Relay_Source_Log_File": "Relay_Master_Log_File",
    "Source_SSL_Allowed": "Master_SSL_Allowed",
    "Source_SSL_CA_File": "Master_SSL_CA_File",
    "Source_SSL_CA_Path": "Master_SSL_CA_Path",
    "Source_SSL_Cert": "Master_SSL_Cert",
    "Source_SSL_Cipher": "Master_SSL_Cipher",
    "Source_SSL_Key": "Master_SSL_Key",
    "Source_SSL_Verify_Server_Cert": "Master_SSL_Verify_Server_Cert",
    "Source_Server_Id": "Master_Server_Id",
    "Source_UUID": "Master_UUID",
    "Source_Info_File": "Master_Info_File",
    "Source_Bind": "Master_Bind",
    "Replica_IO_State": "Slave_IO_State",
    "Replica_SQL_Running_State": "Slave_SQL_Running_State",
    "Source_SSL_Crl": "Master_SSL_Crl",
    "Source_SSL_Crlpath": "Master_SSL_Crlpath",
    "Source_TLS_Version": "Master_TLS_Version",
    "Source_public_key_path": "Master_public_key_path",
}

# ============================================================
# SHOW BINARY LOG STATUS 字段映射（新版 → 旧版）
# MySQL 8.4 中 SHOW BINARY LOG STATUS 的字段名与 SHOW MASTER STATUS 基本一致，
# 如有变化在此补充。
# ============================================================
_BINARY_LOG_STATUS_FIELD_MAP: Dict[str, str] = {}


def get_instance_major_version(address: str) -> Tuple[int, int]:
    """
    从 DBM 元数据获取实例的 MySQL 主版本号。

    直接读取 StorageInstance 表的 version 字段（格式如 "5.7.20"、"8.4.0"）。

    Args:
        address: 实例地址，格式为 "host:port"

    Returns:
        (major, minor) 元组，如 (8, 4)。
        查不到时默认返回 (5, 7)（不翻译，安全回退）。
    """
    cache_key = f"{_VERSION_CACHE_PREFIX}{address}"
    version = cache.get(cache_key)
    if version is not None:
        return version

    try:
        from backend.db_meta.models import StorageInstance

        host, port = address.rsplit(":", 1)
        inst = StorageInstance.objects.get(machine__ip=host, port=int(port))
        if inst.version:
            # version 字段格式如 "5.7.20"、"8.4.0"、"8.0.30"
            parts = inst.version.split(".")
            version = (int(parts[0]), int(parts[1]))
        else:
            version = (5, 7)
    except Exception as e:
        logger.debug("[mysql_replication_compat] failed to get instance version %s %s", address, e)
        version = (5, 7)

    cache.set(cache_key, version, _VERSION_CACHE_TTL)
    return version


def translate_cmds(cmds: List[str], version: Tuple[int, int]) -> Tuple[List[str], List[int]]:
    """
    翻译 SQL 命令列表。

    Args:
        cmds: 原始 SQL 命令列表
        version: MySQL 版本元组，如 (8, 4)

    Returns:
        (翻译后的命令列表, 需要做字段映射的命令索引列表)。
        如果版本 < 8.4，直接返回原始命令和空索引列表。
    """
    if version < (8, 4):
        return cmds, []

    translated = []
    field_map_indices = []
    for i, cmd in enumerate(cmds):
        new_cmd, needs_field_map = _translate_single_cmd(cmd)
        translated.append(new_cmd)
        if needs_field_map:
            field_map_indices.append(i)
    return translated, field_map_indices


def _translate_single_cmd(cmd: str) -> Tuple[str, bool]:
    """
    翻译单条 SQL 命令。

    Args:
        cmd: 原始 SQL 命令

    Returns:
        (翻译后的命令, 是否需要对返回结果做字段映射)
    """
    stripped = cmd.strip()
    for pattern, replacement, needs_field_map in _CMD_PATTERNS:
        match = pattern.match(stripped)
        if match:
            if "CHANGE REPLICATION SOURCE TO" in replacement.upper():
                # CHANGE MASTER TO 需要额外替换参数名
                new_cmd = pattern.sub(replacement, stripped, count=1)
                new_cmd = _translate_change_master_params(new_cmd)
                return new_cmd, needs_field_map
            else:
                new_cmd = pattern.sub(replacement, stripped, count=1)
                return new_cmd, needs_field_map
    return cmd, False


def _translate_change_master_params(cmd: str) -> str:
    """
    替换 CHANGE REPLICATION SOURCE TO 中的参数名。

    将 MASTER_HOST、MASTER_PORT 等旧版参数名替换为 SOURCE_HOST、SOURCE_PORT 等新版参数名。
    大小写不敏感匹配。
    """
    for old_param, new_param in _MASTER_PARAM_MAP.items():
        cmd = re.sub(rf"(?i)\b{old_param}\b", new_param, cmd)
    return cmd


def map_result_fields(result: list, field_map_indices: List[int], remove_original: bool = False) -> list:
    """
    对 DRSApi.rpc 返回的 data（list）中指定索引的 cmd_results 做字段名映射。

    DRSApi.rpc 返回结构：
    [
        {
            "cmd_results": [
                {"table_data": [{"Replica_IO_Running": "Yes", ...}], ...},
                ...
            ],
            ...
        },
        ...
    ]

    Args:
        result: DRSApi.rpc 返回的 data 列表
        field_map_indices: 需要做字段映射的 cmd 索引列表
        remove_original: 是否移除原来的新版字段名，默认 False（保留新旧两个字段名）

    Returns:
        映射后的 result（原地修改并返回）
    """
    if not field_map_indices:
        return result

    for item in result:
        cmd_results = item.get("cmd_results", [])
        for idx in field_map_indices:
            if idx < len(cmd_results):
                table_data = cmd_results[idx].get("table_data", [])
                cmd_results[idx]["table_data"] = [
                    _map_row_fields(row, remove_original=remove_original) for row in table_data
                ]
    return result


def _map_row_fields(row: dict, remove_original: bool = False) -> dict:
    """
    将单行数据中的新版字段名映射为旧版字段名。

    Args:
        row: 单行数据字典
        remove_original: 是否移除原来的新版字段名，默认 False（保留新旧两个字段名）

    对于不在映射表中的字段名，保持原样不变。
    """
    mapped = {}
    for key, value in row.items():
        # 优先查 REPLICA STATUS 映射表
        if key in _REPLICA_STATUS_FIELD_MAP:
            mapped[_REPLICA_STATUS_FIELD_MAP[key]] = value
            if not remove_original:
                mapped[key] = value
        elif key in _BINARY_LOG_STATUS_FIELD_MAP:
            mapped[_BINARY_LOG_STATUS_FIELD_MAP[key]] = value
            if not remove_original:
                mapped[key] = value
        else:
            mapped[key] = value
    return mapped
