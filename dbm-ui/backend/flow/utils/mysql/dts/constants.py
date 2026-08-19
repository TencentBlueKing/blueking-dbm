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
from django.utils.translation import gettext_lazy as _

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

# CC 标准化：Set 名 = get_monitor_set_name(MySQL, DTS_CC_MONITOR_PLUGIN_NAME) → db.mysql.dts
DTS_CC_MONITOR_PLUGIN_NAME = "dts"

# dbbackup 包解压后 myloader 默认相对路径（可通过 MyloaderSpec.myloader_path 覆盖）
DEFAULT_MYLOADER_PATH = "/home/mysql/dbbackup/bin/myloader"
MYSQL_DTS_MYLOADER_BACKUP_DIR_TMPL = "/data/dbbak/{root_id}/dts_myloader/{source_name}"


def get_default_deploy_path(cluster_name: str) -> str:
    return f"{MYSQL_DTS_DEPLOY_BASE_PATH}/{cluster_name}"


def get_full_migrate_data_dir(cluster_name: str, task_name: str) -> str:
    return f"{get_default_deploy_path(cluster_name)}/exported_data/{task_name}"


def get_myloader_backup_dir(root_id: str, source_name: str) -> str:
    return MYSQL_DTS_MYLOADER_BACKUP_DIR_TMPL.format(root_id=root_id, source_name=source_name)


class DtsRegisterMode(StrStructuredEnum):
    CREATE = EnumField("create", _("create"))
    APPEND_WORKER = EnumField("append_worker", _("append_worker"))
    APPEND_MASTER = EnumField("append_master", _("append_master"))


class DtsLifecycleMode(StrStructuredEnum):
    USE_EXISTING = EnumField("use_existing", _("use_existing"))
    DEPLOY_EPHEMERAL = EnumField("deploy_ephemeral", _("deploy_ephemeral"))
    DEPLOY_PERSISTENT = EnumField("deploy_persistent", _("deploy_persistent"))


class FullLoadEngine(StrStructuredEnum):
    BUILTIN = EnumField("builtin", _("builtin"))
    MYLOADER = EnumField("myloader", _("myloader"))


class MigrateTopology(StrStructuredEnum):
    ONE_TO_ONE = EnumField("one_to_one", _("one_to_one"))
    MANY_TO_ONE = EnumField("many_to_one", _("many_to_one"))
    ONE_TO_MANY = EnumField("one_to_many", _("one_to_many"))


class MigrateType(StrStructuredEnum):
    MYSQL_TO_MYSQL = EnumField("mysql_to_mysql", _("mysql_to_mysql"))
    HA_TO_CLUSTER = EnumField("ha_to_cluster", _("ha_to_cluster"))
