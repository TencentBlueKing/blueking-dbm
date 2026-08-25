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

from dataclasses import dataclass
from typing import Dict, List

from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import DBType
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta, _all_actions

# 各组件 DBA 共有的操作，三段的鉴权范围不同，见注释
DBA_SHARED_ACTIONS = [
    # 公共入口。单据与任务流程分别挂在 ticket / flow 拓扑下，申请停在 db_type 时仅覆盖本组件
    ActionEnum.DB_MANAGE,
    ActionEnum.TICKET_VIEW,
    ActionEnum.FLOW_DETAIL,
    # 业务级共享。相关页面未按 dbtype 分 Tab，操作只关联 biz，因此为全业务范围
    ActionEnum.ALERT_SHIELD_MANAGE,
    ActionEnum.NOTIFY_GROUP_MANAGE,
    ActionEnum.BIZ_ASSISTANCE_VARS_CONFIG,
    ActionEnum.BIZ_NOTIFY_CONFIG,
    ActionEnum.RESOURCE_TAG_MANAGE,
    ActionEnum.RISK_MEMO_CREATE,
    ActionEnum.RISK_MEMO_MANAGE,
    # 共享配置。仅关联 db_type，申请停在 db_type 时仅覆盖本组件
    ActionEnum.DBCONFIG_EDIT,
    ActionEnum.MONITOR_POLICY_MANAGE,
    ActionEnum.BIZ_TICKET_CONFIG_SET,
]

# MySQL DBA 专属：Dumper 相关与授权白名单归属 MySQL DBA
MYSQL_DBA_EXTRA_ACTIONS = [
    ActionEnum.IP_WHITELIST_MANAGE,
    ActionEnum.DUMPER_CONFIG_VIEW,
    ActionEnum.DUMPER_CONFIG_UPDATE,
    ActionEnum.DUMPER_CONFIG_DESTROY,
    ActionEnum.TBINLOGDUMPER_INSTALL,
    ActionEnum.TBINLOGDUMPER_ENABLE_DISABLE,
    ActionEnum.TBINLOGDUMPER_REDUCE_NODES,
    ActionEnum.TBINLOGDUMPER_SWITCH_NODES,
]

# 业务只读：业务访问 + 12 个组件的集群详情查看
BIZ_READ_ONLY_ACTIONS = [
    ActionEnum.DB_MANAGE,
    ActionEnum.MYSQL_VIEW,
    ActionEnum.TENDBCLUSTER_VIEW,
    ActionEnum.REDIS_VIEW,
    ActionEnum.MONGODB_VIEW,
    ActionEnum.SQLSERVER_VIEW,
    ActionEnum.ES_VIEW,
    ActionEnum.KAFKA_VIEW,
    ActionEnum.HDFS_VIEW,
    ActionEnum.PULSAR_VIEW,
    ActionEnum.DORIS_VIEW,
    ActionEnum.RIAK_VIEW,
    ActionEnum.ORACLE_VIEW,
]

# 业务运维：部署、备份恢复、授权、分区、销毁启停、告警与单据配置
BIZ_MAINTAIN_ACTIONS = [
    ActionEnum.ALERT_SHIELD_MANAGE,
    ActionEnum.BIZ_ASSISTANCE_VARS_CONFIG,
    ActionEnum.BIZ_NOTIFY_CONFIG,
    ActionEnum.DB_MANAGE,
    ActionEnum.DORIS_ACCESS_ENTRY_VIEW,
    ActionEnum.DORIS_APPLY,
    ActionEnum.DORIS_DESTROY,
    ActionEnum.DORIS_EDIT,
    ActionEnum.DORIS_ENABLE_DISABLE,
    ActionEnum.DORIS_SUBSCRIBE_MONITOR,
    ActionEnum.DORIS_VIEW,
    ActionEnum.ES_ACCESS_ENTRY_VIEW,
    ActionEnum.ES_APPLY,
    ActionEnum.ES_DESTROY,
    ActionEnum.ES_EDIT,
    ActionEnum.ES_ENABLE_DISABLE,
    ActionEnum.ES_LOADBALANCE_MANAGE,
    ActionEnum.ES_SUBSCRIBE_MONITOR,
    ActionEnum.ES_VIEW,
    ActionEnum.FLOW_DETAIL,
    ActionEnum.HDFS_ACCESS_ENTRY_VIEW,
    ActionEnum.HDFS_APPLY,
    ActionEnum.HDFS_DESTROY,
    ActionEnum.HDFS_EDIT,
    ActionEnum.HDFS_ENABLE_DISABLE,
    ActionEnum.HDFS_SUBSCRIBE_MONITOR,
    ActionEnum.HDFS_VIEW,
    ActionEnum.IP_WHITELIST_MANAGE,
    ActionEnum.KAFKA_ACCESS_ENTRY_VIEW,
    ActionEnum.KAFKA_APPLY,
    ActionEnum.KAFKA_DESTROY,
    ActionEnum.KAFKA_EDIT,
    ActionEnum.KAFKA_ENABLE_DISABLE,
    ActionEnum.KAFKA_SUBSCRIBE_MONITOR,
    ActionEnum.KAFKA_VIEW,
    ActionEnum.MONGODB_ACCESS_ENTRY_VIEW,
    ActionEnum.MONGODB_APPLY,
    ActionEnum.MONGODB_AUTHORIZE,
    ActionEnum.MONGODB_BACKUP,
    ActionEnum.MONGODB_DATA_EXPORT,
    ActionEnum.MONGODB_DESTROY,
    ActionEnum.MONGODB_EDIT,
    ActionEnum.MONGODB_ENABLE_DISABLE,
    ActionEnum.MONGODB_EXEC_SCRIPT_APPLY,
    ActionEnum.MONGODB_FULL_BACKUP,
    ActionEnum.MONGODB_LOADBALANCE_MANAGE,
    ActionEnum.MONGODB_PITR_RESTORE,
    ActionEnum.MONGODB_PRIV_MANAGE,
    ActionEnum.MONGODB_REMOVE_NS,
    ActionEnum.MONGODB_RESTORE,
    ActionEnum.MONGODB_SOURCE_ACCESS_VIEW,
    ActionEnum.MONGODB_SUBSCRIBE_MONITOR,
    ActionEnum.MONGODB_TEMPORARY_DESTROY,
    ActionEnum.MONGODB_VIEW,
    ActionEnum.MONGODB_WEBCONSOLE,
    ActionEnum.MONITOR_POLICY_MANAGE,
    ActionEnum.MYSQL_APPLY,
    ActionEnum.MYSQL_AUTHORIZE,
    ActionEnum.MYSQL_DATA_MIGRATE,
    ActionEnum.MYSQL_DESTROY,
    ActionEnum.MYSQL_DUMP_DATA,
    ActionEnum.MYSQL_EDIT,
    ActionEnum.MYSQL_ENABLE_DISABLE,
    ActionEnum.MYSQL_FLASHBACK,
    ActionEnum.MYSQL_HA_DB_TABLE_BACKUP,
    ActionEnum.MYSQL_HA_FULL_BACKUP,
    ActionEnum.MYSQL_IMPORT_SQLFILE,
    ActionEnum.MYSQL_LOADBALANCE_MANAGE,
    ActionEnum.MYSQL_OPENAREA,
    ActionEnum.MYSQL_OPENAREA_MANAGE,
    ActionEnum.MYSQL_PARTITION_MANAGE,
    ActionEnum.MYSQL_PRIV_MANAGE,
    ActionEnum.MYSQL_RENAME_DATABASE,
    ActionEnum.MYSQL_ROLLBACK,
    ActionEnum.MYSQL_ROLLBACK_CLUSTER,
    ActionEnum.MYSQL_SUBSCRIBE_MONITOR,
    ActionEnum.MYSQL_TRUNCATE_DATA,
    ActionEnum.MYSQL_VIEW,
    ActionEnum.MYSQL_WEBCONSOLE,
    ActionEnum.NOTIFY_GROUP_MANAGE,
    ActionEnum.ORACLE_DESTROY,
    ActionEnum.ORACLE_EDIT,
    ActionEnum.ORACLE_ENABLE_DISABLE,
    ActionEnum.ORACLE_EXEC_SCRIPT_APPLY,
    ActionEnum.ORACLE_SUBSCRIBE_MONITOR,
    ActionEnum.ORACLE_VIEW,
    ActionEnum.PULSAR_ACCESS_ENTRY_VIEW,
    ActionEnum.PULSAR_APPLY,
    ActionEnum.PULSAR_DESTROY,
    ActionEnum.PULSAR_EDIT,
    ActionEnum.PULSAR_ENABLE_DISABLE,
    ActionEnum.PULSAR_SUBSCRIBE_MONITOR,
    ActionEnum.PULSAR_VIEW,
    ActionEnum.REDIS_ACCESS_ENTRY_VIEW,
    ActionEnum.REDIS_BACKUP,
    ActionEnum.REDIS_CLUSTER_APPLY,
    ActionEnum.REDIS_CLUSTER_DATA_COPY,
    ActionEnum.REDIS_CLUSTER_ROLLBACK_DATA_COPY,
    ActionEnum.REDIS_DATA_STRUCTURE,
    ActionEnum.REDIS_DATA_STRUCTURE_TASK_DELETE,
    ActionEnum.REDIS_DESTROY,
    ActionEnum.REDIS_EDIT,
    ActionEnum.REDIS_HOT_KEY_ANALYSIS,
    ActionEnum.REDIS_INSTANCE_DESTROY,
    ActionEnum.REDIS_KEYS_DELETE,
    ActionEnum.REDIS_KEYS_EXTRACT,
    ActionEnum.REDIS_KEYSTAT,
    ActionEnum.REDIS_LOADBALANCE_MANAGE,
    ActionEnum.REDIS_OPEN_CLOSE,
    ActionEnum.REDIS_PURGE,
    ActionEnum.REDIS_SOURCE_ACCESS_VIEW,
    ActionEnum.REDIS_SUBSCRIBE_MONITOR,
    ActionEnum.REDIS_VIEW,
    ActionEnum.REDIS_WEBCONSOLE,
    ActionEnum.RESOURCE_TAG_MANAGE,
    ActionEnum.RIAK_ACCESS_ENTRY_VIEW,
    ActionEnum.RIAK_CLUSTER_APPLY,
    ActionEnum.RIAK_CLUSTER_DESTROY,
    ActionEnum.RIAK_EDIT,
    ActionEnum.RIAK_ENABLE_DISABLE,
    ActionEnum.RIAK_VIEW,
    ActionEnum.RISK_MEMO_CREATE,
    ActionEnum.RISK_MEMO_MANAGE,
    ActionEnum.SQLSERVER_APPLY,
    ActionEnum.SQLSERVER_AUTHORIZE,
    ActionEnum.SQLSERVER_BACKUP_DBS,
    ActionEnum.SQLSERVER_CLEAR_DBS,
    ActionEnum.SQLSERVER_DATA_EXPORT,
    ActionEnum.SQLSERVER_DBRENAME,
    ActionEnum.SQLSERVER_DESTROY,
    ActionEnum.SQLSERVER_EDIT,
    ActionEnum.SQLSERVER_ENABLE_DISABLE,
    ActionEnum.SQLSERVER_FULL_MIGRATE,
    ActionEnum.SQLSERVER_IMPORT_SQLFILE,
    ActionEnum.SQLSERVER_INCR_MIGRATE,
    ActionEnum.SQLSERVER_PRIV_MANAGE,
    ActionEnum.SQLSERVER_ROLLBACK,
    ActionEnum.SQLSERVER_ROLLBACK_LOCAL,
    ActionEnum.SQLSERVER_SUBSCRIBE_MONITOR,
    ActionEnum.SQLSERVER_VIEW,
    ActionEnum.TENDBCLUSTER_APPLY,
    ActionEnum.TENDBCLUSTER_AUTHORIZE,
    ActionEnum.TENDBCLUSTER_DATA_MIGRATE,
    ActionEnum.TENDBCLUSTER_DB_TABLE_BACKUP,
    ActionEnum.TENDBCLUSTER_DESTROY,
    ActionEnum.TENDBCLUSTER_DUMP_DATA,
    ActionEnum.TENDBCLUSTER_EDIT,
    ActionEnum.TENDBCLUSTER_ENABLE_DISABLE,
    ActionEnum.TENDBCLUSTER_FLASHBACK,
    ActionEnum.TENDBCLUSTER_FULL_BACKUP,
    ActionEnum.TENDBCLUSTER_IMPORT_SQLFILE,
    ActionEnum.TENDBCLUSTER_LOADBALANCE_MANAGE,
    ActionEnum.TENDBCLUSTER_OPENAREA,
    ActionEnum.TENDBCLUSTER_OPENAREA_MANAGE,
    ActionEnum.TENDBCLUSTER_PARTITION_MANAGE,
    ActionEnum.TENDBCLUSTER_PRIV_MANAGE,
    ActionEnum.TENDBCLUSTER_RENAME_DATABASE,
    ActionEnum.TENDBCLUSTER_ROLLBACK,
    ActionEnum.TENDBCLUSTER_ROLLBACK_CLUSTER,
    ActionEnum.TENDBCLUSTER_SUBSCRIBE_MONITOR,
    ActionEnum.TENDBCLUSTER_TEMPORARY_DESTROY,
    ActionEnum.TENDBCLUSTER_TRUNCATE_DATABASE,
    ActionEnum.TENDBCLUSTER_VIEW,
    ActionEnum.TENDBCLUSTER_WEBCONSOLE,
    ActionEnum.TICKET_VIEW,
]

# 业务开发：查看、部署、授权、备份导出、回档构造、连接信息、SQL执行等
BIZ_DEVELOPER_ACTIONS = [
    ActionEnum.DB_MANAGE,
    ActionEnum.DORIS_ACCESS_ENTRY_VIEW,
    ActionEnum.DORIS_APPLY,
    ActionEnum.DORIS_EDIT,
    ActionEnum.DORIS_SUBSCRIBE_MONITOR,
    ActionEnum.DORIS_VIEW,
    ActionEnum.ES_ACCESS_ENTRY_VIEW,
    ActionEnum.ES_APPLY,
    ActionEnum.ES_EDIT,
    ActionEnum.ES_LOADBALANCE_MANAGE,
    ActionEnum.ES_SUBSCRIBE_MONITOR,
    ActionEnum.ES_VIEW,
    ActionEnum.HDFS_ACCESS_ENTRY_VIEW,
    ActionEnum.HDFS_APPLY,
    ActionEnum.HDFS_EDIT,
    ActionEnum.HDFS_SUBSCRIBE_MONITOR,
    ActionEnum.HDFS_VIEW,
    ActionEnum.IP_WHITELIST_MANAGE,
    ActionEnum.KAFKA_ACCESS_ENTRY_VIEW,
    ActionEnum.KAFKA_APPLY,
    ActionEnum.KAFKA_EDIT,
    ActionEnum.KAFKA_SUBSCRIBE_MONITOR,
    ActionEnum.KAFKA_VIEW,
    ActionEnum.MONGODB_ACCESS_ENTRY_VIEW,
    ActionEnum.MONGODB_APPLY,
    ActionEnum.MONGODB_AUTHORIZE,
    ActionEnum.MONGODB_BACKUP,
    ActionEnum.MONGODB_DATA_EXPORT,
    ActionEnum.MONGODB_EDIT,
    ActionEnum.MONGODB_EXEC_SCRIPT_APPLY,
    ActionEnum.MONGODB_FULL_BACKUP,
    ActionEnum.MONGODB_LOADBALANCE_MANAGE,
    ActionEnum.MONGODB_PITR_RESTORE,
    ActionEnum.MONGODB_PRIV_MANAGE,
    ActionEnum.MONGODB_REMOVE_NS,
    ActionEnum.MONGODB_RESTORE,
    ActionEnum.MONGODB_SOURCE_ACCESS_VIEW,
    ActionEnum.MONGODB_SUBSCRIBE_MONITOR,
    ActionEnum.MONGODB_VIEW,
    ActionEnum.MONGODB_WEBCONSOLE,
    ActionEnum.MYSQL_APPLY,
    ActionEnum.MYSQL_AUTHORIZE,
    ActionEnum.MYSQL_DATA_MIGRATE,
    ActionEnum.MYSQL_DUMP_DATA,
    ActionEnum.MYSQL_EDIT,
    ActionEnum.MYSQL_FLASHBACK,
    ActionEnum.MYSQL_HA_DB_TABLE_BACKUP,
    ActionEnum.MYSQL_HA_FULL_BACKUP,
    ActionEnum.MYSQL_IMPORT_SQLFILE,
    ActionEnum.MYSQL_LOADBALANCE_MANAGE,
    ActionEnum.MYSQL_PARTITION_MANAGE,
    ActionEnum.MYSQL_PRIV_MANAGE,
    ActionEnum.MYSQL_RENAME_DATABASE,
    ActionEnum.MYSQL_ROLLBACK,
    ActionEnum.MYSQL_ROLLBACK_CLUSTER,
    ActionEnum.MYSQL_SUBSCRIBE_MONITOR,
    ActionEnum.MYSQL_TRUNCATE_DATA,
    ActionEnum.MYSQL_VIEW,
    ActionEnum.MYSQL_WEBCONSOLE,
    ActionEnum.ORACLE_EDIT,
    ActionEnum.ORACLE_EXEC_SCRIPT_APPLY,
    ActionEnum.ORACLE_SUBSCRIBE_MONITOR,
    ActionEnum.ORACLE_VIEW,
    ActionEnum.PULSAR_ACCESS_ENTRY_VIEW,
    ActionEnum.PULSAR_APPLY,
    ActionEnum.PULSAR_EDIT,
    ActionEnum.PULSAR_SUBSCRIBE_MONITOR,
    ActionEnum.PULSAR_VIEW,
    ActionEnum.REDIS_ACCESS_ENTRY_VIEW,
    ActionEnum.REDIS_BACKUP,
    ActionEnum.REDIS_CLUSTER_APPLY,
    ActionEnum.REDIS_CLUSTER_DATA_COPY,
    ActionEnum.REDIS_CLUSTER_ROLLBACK_DATA_COPY,
    ActionEnum.REDIS_DATA_STRUCTURE,
    ActionEnum.REDIS_DATA_STRUCTURE_TASK_DELETE,
    ActionEnum.REDIS_EDIT,
    ActionEnum.REDIS_HOT_KEY_ANALYSIS,
    ActionEnum.REDIS_KEYS_DELETE,
    ActionEnum.REDIS_KEYS_EXTRACT,
    ActionEnum.REDIS_KEYSTAT,
    ActionEnum.REDIS_LOADBALANCE_MANAGE,
    ActionEnum.REDIS_PURGE,
    ActionEnum.REDIS_SOURCE_ACCESS_VIEW,
    ActionEnum.REDIS_SUBSCRIBE_MONITOR,
    ActionEnum.REDIS_VIEW,
    ActionEnum.REDIS_WEBCONSOLE,
    ActionEnum.RIAK_ACCESS_ENTRY_VIEW,
    ActionEnum.RIAK_CLUSTER_APPLY,
    ActionEnum.RIAK_EDIT,
    ActionEnum.RIAK_VIEW,
    ActionEnum.SQLSERVER_APPLY,
    ActionEnum.SQLSERVER_AUTHORIZE,
    ActionEnum.SQLSERVER_BACKUP_DBS,
    ActionEnum.SQLSERVER_CLEAR_DBS,
    ActionEnum.SQLSERVER_DATA_EXPORT,
    ActionEnum.SQLSERVER_DBRENAME,
    ActionEnum.SQLSERVER_EDIT,
    ActionEnum.SQLSERVER_FULL_MIGRATE,
    ActionEnum.SQLSERVER_IMPORT_SQLFILE,
    ActionEnum.SQLSERVER_INCR_MIGRATE,
    ActionEnum.SQLSERVER_PRIV_MANAGE,
    ActionEnum.SQLSERVER_ROLLBACK,
    ActionEnum.SQLSERVER_ROLLBACK_LOCAL,
    ActionEnum.SQLSERVER_SUBSCRIBE_MONITOR,
    ActionEnum.SQLSERVER_VIEW,
    ActionEnum.TENDBCLUSTER_APPLY,
    ActionEnum.TENDBCLUSTER_AUTHORIZE,
    ActionEnum.TENDBCLUSTER_DATA_MIGRATE,
    ActionEnum.TENDBCLUSTER_DB_TABLE_BACKUP,
    ActionEnum.TENDBCLUSTER_DUMP_DATA,
    ActionEnum.TENDBCLUSTER_EDIT,
    ActionEnum.TENDBCLUSTER_FLASHBACK,
    ActionEnum.TENDBCLUSTER_FULL_BACKUP,
    ActionEnum.TENDBCLUSTER_IMPORT_SQLFILE,
    ActionEnum.TENDBCLUSTER_LOADBALANCE_MANAGE,
    ActionEnum.TENDBCLUSTER_PARTITION_MANAGE,
    ActionEnum.TENDBCLUSTER_PRIV_MANAGE,
    ActionEnum.TENDBCLUSTER_RENAME_DATABASE,
    ActionEnum.TENDBCLUSTER_ROLLBACK,
    ActionEnum.TENDBCLUSTER_ROLLBACK_CLUSTER,
    ActionEnum.TENDBCLUSTER_SUBSCRIBE_MONITOR,
    ActionEnum.TENDBCLUSTER_TRUNCATE_DATABASE,
    ActionEnum.TENDBCLUSTER_VIEW,
    ActionEnum.TENDBCLUSTER_WEBCONSOLE,
    ActionEnum.TICKET_VIEW,
]


@dataclass
class RoleMeta:
    """
    IAM V4 角色定义。V4 以角色为申请主入口，用户申请的是角色而非单个操作，
    """

    id: str
    name: str
    description: str
    # 角色包含的操作。为 None 表示包含全部已注册操作，用于平台管理员随注册面自动增减
    actions: List[ActionMeta] = None

    def get_actions(self) -> List[ActionMeta]:
        """角色包含的动作，未同步到V4的动作不纳入"""
        actions = _all_actions.values() if self.actions is None else self.actions
        return [action for action in actions if not action.is_disabled_v4()]

    def to_json_v4(self) -> Dict:
        # 角色内动作的授权维度取动作自身关联的资源类型，无关资源的动作则为空
        actions = [
            {"id": action.id, "resource_type_id": action.to_json_v4()["resource_type_id"]}
            for action in self.get_actions()
        ]
        return {
            "id": self.id,
            "name": str(self.name),
            "description": str(self.description or self.name),
            "actions": actions,
        }


def _make_dba_actions(db_type: str) -> List[ActionMeta]:
    """
    按组件生成 DBA 的操作集合：本组件全部前缀操作 + 各组件共有的操作。
    MySQL 额外含 Dumper 与授权白名单
    """
    component_actions = [
        action for action_id, action in _all_actions.items() if action_id.startswith("{}_".format(db_type))
    ]
    extra_actions = MYSQL_DBA_EXTRA_ACTIONS if db_type in [DBType.MySQL, DBType.TenDBCluster] else []
    actions = DBA_SHARED_ACTIONS + component_actions + extra_actions
    # ActionMeta 不可哈希，按 id 去重后按 id 排序
    return sorted({action.id: action for action in actions}.values(), key=lambda action: action.id)


class RoleEnum:
    """role 枚举类"""

    # ---------------- 业务侧：申请从业务开始，可选业务整授、指定集群或「无限制」 ----------------
    BIZ_READ_ONLY = RoleMeta(
        id="dbm_biz_read_only",
        name=_("业务只读"),
        description=_("可访问业务，并查看各组件集群详情。"),
        actions=BIZ_READ_ONLY_ACTIONS,
    )
    BIZ_MAINTAIN = RoleMeta(
        id="dbm_biz_maintain",
        name=_("业务运维"),
        description=_("业务下部署、备份恢复、授权、分区、销毁、启停、告警与单据配置。"),
        actions=BIZ_MAINTAIN_ACTIONS,
    )
    BIZ_DEVELOPER = RoleMeta(
        id="dbm_biz_developer",
        name=_("业务开发"),
        description=_("查看、部署、授权、分区、备份、导出、告警订阅、回档/构造/迁移、连接信息、SQL执行等。"),
        actions=BIZ_DEVELOPER_ACTIONS,
    )

    # ---------------- 组件 DBA：按组件各一个角色，为本组件的运维超集 ----------------
    MYSQL_DBA = RoleMeta(
        id="dbm_mysql_dba",
        name=_("MySQL DBA"),
        description=_("拥有本业务 MySQL 全部运维权限（含运维聚合、扩缩容/切换、临时密码、Dumper、授权白名单）。"),
        actions=_make_dba_actions(DBType.MySQL),
    )
    TENDBCLUSTER_DBA = RoleMeta(
        id="dbm_tendbcluster_dba",
        name=_("TenDBCluster DBA"),
        description=_("拥有本业务 TenDBCluster 全部运维权限（含运维聚合、扩缩容/切换、临时密码）。"),
        actions=_make_dba_actions(DBType.TenDBCluster),
    )
    REDIS_DBA = RoleMeta(
        id="dbm_redis_dba",
        name=_("Redis DBA"),
        description=_("拥有本业务 Redis 全部运维权限（含运维聚合、扩缩容/切换）。"),
        actions=_make_dba_actions(DBType.Redis),
    )
    MONGODB_DBA = RoleMeta(
        id="dbm_mongodb_dba",
        name=_("MongoDB DBA"),
        description=_("拥有本业务 MongoDB 全部运维权限（含运维聚合、扩缩容/切换）。"),
        actions=_make_dba_actions(DBType.MongoDB),
    )
    SQLSERVER_DBA = RoleMeta(
        id="dbm_sqlserver_dba",
        name=_("SQLServer DBA"),
        description=_("拥有本业务 SQLServer 全部运维权限（含运维聚合、扩缩容/切换、临时密码）。"),
        actions=_make_dba_actions(DBType.Sqlserver),
    )
    ES_DBA = RoleMeta(
        id="dbm_es_dba",
        name=_("ES DBA"),
        description=_("拥有本业务 ES 全部运维权限（含运维聚合、扩缩容/切换）。"),
        actions=_make_dba_actions(DBType.Es),
    )
    KAFKA_DBA = RoleMeta(
        id="dbm_kafka_dba",
        name=_("Kafka DBA"),
        description=_("拥有本业务 Kafka 全部运维权限（含运维聚合、扩缩容/切换）。"),
        actions=_make_dba_actions(DBType.Kafka),
    )
    HDFS_DBA = RoleMeta(
        id="dbm_hdfs_dba",
        name=_("HDFS DBA"),
        description=_("拥有本业务 HDFS 全部运维权限（含运维聚合、扩缩容/切换）。"),
        actions=_make_dba_actions(DBType.Hdfs),
    )
    PULSAR_DBA = RoleMeta(
        id="dbm_pulsar_dba",
        name=_("Pulsar DBA"),
        description=_("拥有本业务 Pulsar 全部运维权限（含运维聚合、扩缩容/切换）。"),
        actions=_make_dba_actions(DBType.Pulsar),
    )
    DORIS_DBA = RoleMeta(
        id="dbm_doris_dba",
        name=_("Doris DBA"),
        description=_("拥有本业务 Doris 全部运维权限（含运维聚合、扩缩容/切换）。"),
        actions=_make_dba_actions(DBType.Doris),
    )
    RIAK_DBA = RoleMeta(
        id="dbm_riak_dba",
        name=_("Riak DBA"),
        description=_("拥有本业务 Riak 全部运维权限（含运维聚合、扩缩容/切换）。"),
        actions=_make_dba_actions(DBType.Riak),
    )
    ORACLE_DBA = RoleMeta(
        id="dbm_oracle_dba",
        name=_("Oracle DBA"),
        description=_("拥有本业务 Oracle 全部运维权限（含运维聚合、扩缩容/切换）。"),
        actions=_make_dba_actions(DBType.Oracle),
    )

    # ---------------- 平台管理员：含全部已注册操作，随注册面自动增减 ----------------
    PLATFORM_ADMIN = RoleMeta(
        id="dbm_platform_admin",
        name=_("平台管理员"),
        description=_("拥有平台全部已注册操作（含全局设置、全部组件）。"),
        # None表示所有已注册操作，[]表示无动作
        actions=None,
    )


# 角色的动作列表不允许为空，无动作的角色不注册到IAM
_all_roles = {
    role.id: role for role in RoleEnum.__dict__.values() if isinstance(role, RoleMeta) and role.get_actions()
}
