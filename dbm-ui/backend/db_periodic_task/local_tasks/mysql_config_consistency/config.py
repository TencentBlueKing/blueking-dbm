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
from dataclasses import dataclass, field, fields
from typing import List

from django.utils.translation import gettext as _

from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings

logger = logging.getLogger("root")

# 存储层关键配置高危项（差异标 abnormal；已排除 sync_binlog / innodb_flush_log_at_trx_commit / gtid_mode / enforce_gtid_consistency）
STORAGE_HIGH_IMPACT_VARS: List[str] = [
    "log_bin",
    "binlog_format",
    "binlog_row_image",
    "transaction_isolation",
    "tx_isolation",
    "sql_mode",
    "character_set_server",
    "collation_server",
    "lower_case_table_names",
    "default_storage_engine",
    "default_time_zone",
    "time_zone",
    "default_table_encryption",
    # 对齐 Spider 模拟执行主分片参数一致性检查 4 项
    "innodb_large_prefix",
    "innodb_strict_mode",
    "rocksdb_large_prefix",
    "rocksdb_strict_collation_check",
]

# 存储层关键配置预警项（差异标 warning）
STORAGE_WARN_VARS: List[str] = [
    "max_connections",
    "max_allowed_packet",
    "wait_timeout",
    "interactive_timeout",
    "innodb_lock_wait_timeout",
    "innodb_autoinc_lock_mode",
    "explicit_defaults_for_timestamp",
    "group_concat_max_len",
    "log_bin_trust_function_creators",
    "slave_exec_mode",
]

# Spider Master 间高危关键配置（差异标 abnormal）
SPIDER_HIGH_IMPACT_VARS: List[str] = [
    "sql_mode",
    "character_set_server",
    "collation_server",
    "lower_case_table_names",
    "transaction_isolation",
    "tx_isolation",
    "time_zone",
    "ddl_execute_by_ctl",
    "spider_support_xa",
    "spider_internal_xa",
    "spider_sync_autocommit",
    "spider_sync_time_zone",
    "spider_bgs_mode",
    "spider_bgs_dml",
    "spider_query_one_shard",
    "spider_transaction_one_shard",
]

# Spider Master 间预警关键配置（差异标 warning）
SPIDER_WARN_VARS: List[str] = [
    "max_connections",
    "max_allowed_packet",
    "wait_timeout",
    "interactive_timeout",
    "spider_net_read_timeout",
    "spider_net_write_timeout",
    "spider_conn_recycle_mode",
    "group_concat_max_len",
]

# 布尔语义变量：对比时将 ON/1/true 与 OFF/0/false 归一化，避免等价写法误报
BOOL_NORMALIZE_VARS: List[str] = [
    "log_bin",
    "default_table_encryption",
    "innodb_large_prefix",
    "innodb_strict_mode",
    "rocksdb_large_prefix",
    "rocksdb_strict_collation_check",
    "explicit_defaults_for_timestamp",
    "log_bin_trust_function_creators",
    "ddl_execute_by_ctl",
    "spider_support_xa",
    "spider_internal_xa",
    "spider_sync_autocommit",
    "spider_sync_time_zone",
    "spider_bgs_dml",
    "spider_query_one_shard",
    "spider_transaction_one_shard",
]


def _dedup_vars(*groups: List[str]) -> List[str]:
    ordered: List[str] = []
    seen = set()
    for group in groups:
        for var in group or []:
            name = str(var).strip()
            if name and name not in seen:
                seen.add(name)
                ordered.append(name)
    return ordered


@dataclass
class MysqlConfigConsistencyConfig:
    """MySQL / TenDBCluster 配置一致性巡检动态配置（可由 SystemSettings 覆盖）。"""

    enabled: bool = True
    bizs_ignored: List[int] = field(default_factory=list)
    clusters_ignored: List[int] = field(default_factory=list)
    check_spider_version: bool = True
    dispatch_window_seconds: int = 1800
    retention_days: int = 90

    @property
    def storage_whitelist(self) -> List[str]:
        return _dedup_vars(STORAGE_HIGH_IMPACT_VARS, STORAGE_WARN_VARS)

    @property
    def spider_whitelist(self) -> List[str]:
        return _dedup_vars(SPIDER_HIGH_IMPACT_VARS, SPIDER_WARN_VARS)

    @property
    def tendbcluster_query_variables(self) -> List[str]:
        extra = ["version"] if self.check_spider_version else []
        return _dedup_vars(self.storage_whitelist, self.spider_whitelist, extra)

    @classmethod
    def from_settings(cls) -> "MysqlConfigConsistencyConfig":
        raw = SystemSettings.get_setting_value(
            SystemSettingsEnum.MYSQL_CONFIG_CONSISTENCY_CHECK.value,
            default={},
        )
        if not isinstance(raw, dict):
            if raw:
                logger.warning(_("配置一致性巡检配置格式非字典，已回退默认值: {}").format(type(raw).__name__))
            return cls()

        valid_keys = {f.name for f in fields(cls)}
        filtered = {key: val for key, val in raw.items() if key in valid_keys and val is not None}
        return cls(**filtered)
