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
import posixpath
import re

from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy

from blue_krill.data_types.enum import EnumField, StrStructuredEnum

MYSQL_DTS_DEPLOY_BASE_PATH = "/data/dts"
MYSQL_DTS_MASTER_PORT = 18301
MYSQL_DTS_WORKER_PORT = 18501
# 与官方 mysql-dts 包样例 conf 一致（dm-master.toml peer-urls）
MYSQL_DTS_MASTER_PEER_PORT = 18401
MYSQL_DTS_VERSION_SERIES = "latest"
MYSQL_DTS_VERIFY_RETRY_INTERVAL = 5
# 部署验收最长等待约 60s（12 * 5s）
MYSQL_DTS_VERIFY_MAX_RETRIES = 12
# 兼容旧版 MySQL（用户名 ≤16）；前缀 + 随机后缀总长不得超过 MYSQL_DTS_MIGRATE_USER_MAX_LENGTH
MYSQL_DTS_MIGRATE_USER_PREFIX = "dts_m_"
MYSQL_DTS_MIGRATE_USER_MAX_LENGTH = 16
MYSQL_DTS_MIGRATE_USER_SUFFIX_LENGTH = 8
# Flow 内嵌追平轮询：间隔 / 连续追平次数 / API 失败 streak
MYSQL_DTS_CATCHUP_POLL_INTERVAL = 15
MYSQL_DTS_CATCHUP_REQUIRED_CONSECUTIVE = 3
MYSQL_DTS_CATCHUP_MAX_FAIL_STREAK = 20
# Flow 内嵌全量导入完成轮询：间隔 / API 失败 streak（无连续成功次数要求）
MYSQL_DTS_FULL_LOAD_POLL_INTERVAL = 15
MYSQL_DTS_FULL_LOAD_MAX_FAIL_STREAK = 20
# 建任务平台强制：排序集补齐；增量 checkpoint 间隔（秒）。单据 engine_options 不得覆盖。
DTS_COLLATION_COMPATIBLE_STRICT = "strict"
DTS_CHECKPOINT_FLUSH_INTERVAL_DEFAULT = 5
# builtin Dump 全局锁超时（32004）合计尝试次数（含首次）
DTS_DUMP_GLOBAL_LOCK_MAX_ATTEMPTS = 3

# CC 标准化：Set 名 = get_monitor_set_name(MySQL, DTS_CC_MONITOR_PLUGIN_NAME) → db.mysql.dts
DTS_CC_MONITOR_PLUGIN_NAME = "dts"

# dbbackup 包解压后 myloader 默认相对路径（可通过 MyloaderSpec.myloader_path 覆盖）
DEFAULT_MYLOADER_PATH = "/home/mysql/dbbackup/bin/myloader"
MYSQL_DTS_MYLOADER_BACKUP_DIR_TMPL = "/data/dbbak/{root_id}/dts_myloader/{source_name}"

_DTS_CLUSTER_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_DTS_DEPLOY_PATH_RE = re.compile(r"^/[A-Za-z0-9._/-]+$")


def validate_dts_cluster_name(cluster_name: str) -> str:
    """空串放行（可选字段）；非空则只允许字母数字、点、下划线和短横线。"""
    name = (cluster_name or "").strip()
    if not name:
        return ""
    if not _DTS_CLUSTER_NAME_RE.fullmatch(name):
        raise ValueError(_("DTS cluster_name 仅允许字母数字、点、下划线和短横线"))
    return name


def validate_dts_deploy_path(deploy_path: str) -> str:
    """空串放行；非空必须是 {MYSQL_DTS_DEPLOY_BASE_PATH} 下的绝对路径，禁止 .. 与 shell 元字符。"""
    raw = (deploy_path or "").strip()
    if not raw:
        return ""
    if any(part == ".." for part in raw.split("/")):
        raise ValueError(_("DTS deploy_path 不允许包含 .."))
    if not raw.startswith("/"):
        raise ValueError(_("DTS deploy_path 必须是绝对路径"))
    normalized = posixpath.normpath(raw)
    if not _DTS_DEPLOY_PATH_RE.fullmatch(normalized):
        raise ValueError(_("DTS deploy_path 含非法字符"))
    base = MYSQL_DTS_DEPLOY_BASE_PATH.rstrip("/")
    if normalized != base and not normalized.startswith(base + "/"):
        raise ValueError(_("DTS deploy_path 必须位于 {} 下").format(base))
    return normalized


def get_default_deploy_path(cluster_name: str) -> str:
    name = validate_dts_cluster_name(cluster_name)
    if not name:
        raise ValueError(_("DTS cluster_name 为空，无法生成 deploy_path"))
    return f"{MYSQL_DTS_DEPLOY_BASE_PATH}/{name}"


def get_full_migrate_data_dir(cluster_name: str, task_name: str) -> str:
    return f"{get_default_deploy_path(cluster_name)}/exported_data/{task_name}"


def get_myloader_backup_dir(root_id: str, source_name: str) -> str:
    return MYSQL_DTS_MYLOADER_BACKUP_DIR_TMPL.format(root_id=root_id, source_name=source_name)


class DtsRegisterMode(StrStructuredEnum):
    CREATE = EnumField("create", _lazy("create"))
    APPEND_WORKER = EnumField("append_worker", _lazy("append_worker"))
    APPEND_MASTER = EnumField("append_master", _lazy("append_master"))


class DtsLifecycleMode(StrStructuredEnum):
    USE_EXISTING = EnumField("use_existing", _lazy("use_existing"))
    DEPLOY = EnumField("deploy", _lazy("deploy"))


class FullLoadEngine(StrStructuredEnum):
    BUILTIN = EnumField("builtin", _lazy("builtin"))
    MYLOADER = EnumField("myloader", _lazy("myloader"))


class MigrateTopology(StrStructuredEnum):
    ONE_TO_ONE = EnumField("one_to_one", _lazy("one_to_one"))
    MANY_TO_ONE = EnumField("many_to_one", _lazy("many_to_one"))
    ONE_TO_MANY = EnumField("one_to_many", _lazy("one_to_many"))


class MigrateType(StrStructuredEnum):
    MYSQL_TO_MYSQL = EnumField("mysql_to_mysql", _lazy("mysql_to_mysql"))
    HA_TO_CLUSTER = EnumField("ha_to_cluster", _lazy("ha_to_cluster"))
