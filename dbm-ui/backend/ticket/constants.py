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
from typing import Any, Optional

from django.utils.translation import ugettext_lazy as _

from backend.configuration.constants import DBType
from backend.db_meta.exceptions import ClusterExclusiveOperateException
from backend.flow.consts import StateType
from backend.ticket.exceptions import TicketBaseException
from blue_krill.data_types.enum import EnumField, StructuredEnum


class InstanceType(str, StructuredEnum):
    STORAGE = EnumField("storage", _("storage"))
    PROXY = EnumField("proxy", _("proxy"))


class TodoType(str, StructuredEnum):
    """
    待办类型
    """

    APPROVE = EnumField("APPROVE", _("主流程-人工确认"))
    INNER_APPROVE = EnumField("INNER_APPROVE", _("自动化流程-人工确认"))
    RESOURCE_REPLENISH = EnumField("RESOURCE_REPLENISH", _("资源补货"))


class CountType(str, StructuredEnum):
    """
    单据计数类型
    """

    MY_TODO = EnumField("MY_TODO", _("我的待办"))
    MY_APPROVE = EnumField("MY_APPROVE", _("我的申请"))


class TodoStatus(str, StructuredEnum):
    """
    待办状态枚举
       TODO -> (RUNNING，可选) -> DONE_SUCCESS
                            | -> DONE_FAILED
    """

    TODO = EnumField("TODO", _("待处理"))
    RUNNING = EnumField("RUNNING", _("处理中"))
    DONE_SUCCESS = EnumField("DONE_SUCCESS", _("已处理"))
    DONE_FAILED = EnumField("DONE_FAILED", _("已终止"))


class ResourceApplyErrCode(int, StructuredEnum):
    """
    资源申请错误码
    """

    RESOURCE_LAKE = EnumField(60001, _("资源不足"))
    RESOURCE_LOCK_FAIL = EnumField(60002, _("获取资源所失败"))
    RESOURCE_PARAMS_INVALID = EnumField(60003, _("参数合法性校验失败"))
    RESOURCE_MACHINE_FAIL = EnumField(60004, _("锁定返回机器失败"))


DONE_STATUS = [TodoStatus.DONE_SUCCESS, TodoStatus.DONE_FAILED]


class TicketStatus(str, StructuredEnum):
    """单据状态枚举"""

    PENDING = EnumField("PENDING", _("等待中"))
    RUNNING = EnumField("RUNNING", _("执行中"))
    SUCCEEDED = EnumField("SUCCEEDED", _("成功"))
    FAILED = EnumField("FAILED", _("失败"))
    REVOKED = EnumField("REVOKED", _("撤销"))
    TERMINATED = EnumField("TERMINATED", _("终止"))


class TicketFlowStatus(str, StructuredEnum):
    """单据流程状态枚举类"""

    PENDING = EnumField("PENDING", _("等待中"))
    RUNNING = EnumField("RUNNING", _("执行中"))
    SUCCEEDED = EnumField("SUCCEEDED", _("成功"))
    TERMINATED = EnumField("TERMINATED", _("终止"))
    FAILED = EnumField("FAILED", _("失败"))
    REVOKED = EnumField("REVOKED", _("撤销"))
    SKIPPED = EnumField("SKIPPED", _("跳过"))


FLOW_FINISHED_STATUS = [TicketFlowStatus.SKIPPED, TicketStatus.SUCCEEDED]
FLOW_NOT_EXECUTE_STATUS = [TicketFlowStatus.SKIPPED, TicketStatus.PENDING]

BAMBOO_STATE__TICKET_STATE_MAP = {
    StateType.FINISHED.value: TicketFlowStatus.SUCCEEDED.value,
    StateType.FAILED.value: TicketFlowStatus.FAILED.value,
    # bamboo engine流程的撤销对应单据flow的终止
    StateType.REVOKED.value: TicketFlowStatus.TERMINATED.value,
    StateType.RUNNING.value: TicketFlowStatus.RUNNING.value,
}

EXCLUSIVE_TICKET_EXCEL_PATH = "backend/ticket/exclusive_ticket.xlsx"


class TicketEnumField(EnumField):
    """ticket专属枚举类，目前用于自动注册iam"""

    def __iam__init__(self, subgroup: str, register_iam: bool):
        """iam所需的初始化字段"""
        self.subgroup = subgroup or _("工具箱")
        self.register_iam = register_iam

    def __init__(self, real_value: Any, label: Optional[str] = None, subgroup: str = None, register_iam: bool = True):
        super().__init__(real_value, label, is_reserved=False)
        self.__iam__init__(subgroup, register_iam)


class TicketType(str, StructuredEnum):
    @classmethod
    def get_choice_value(cls, label: str) -> str:
        """Get the value of field member by label"""

        members = cls.get_field_members()
        for field in members.values():
            if label in field.label:
                return field.real_value

        return label

    @classmethod
    def get_ticket_type_by_db(cls, db_type):
        """找到相关type的单据"""
        db_type = db_type.upper()
        ticket_types = [t for t in cls.get_values() if db_type in t]
        return ticket_types

    @classmethod
    def get_db_type_by_ticket(cls, ticket_type):
        """根据单据类型找到组件类型"""
        db_type = ticket_type.upper().split("_")[0].lower()
        if db_type == "TBINLOGDUMPER":
            return DBType.MySQL.value
        if db_type in DBType.get_values():
            return db_type
        else:
            raise TicketBaseException(_("无法找到{}关联的组件类型").format(ticket_type))

    # fmt: off
    # MYSQL
    MYSQL_SINGLE_APPLY = TicketEnumField("MYSQL_SINGLE_APPLY", _("MySQL 单节点部署"), register_iam=False)
    MYSQL_ADD_SLAVE = TicketEnumField("MYSQL_ADD_SLAVE", _("MySQL 添加从库"), _("集群维护"))
    MYSQL_RESTORE_SLAVE = TicketEnumField("MYSQL_RESTORE_SLAVE", _("MySQL Slave重建"), _("集群维护"))
    MYSQL_RESTORE_LOCAL_SLAVE = TicketEnumField("MYSQL_RESTORE_LOCAL_SLAVE", _("MySQL Slave原地重建"), _("集群维护"))
    MYSQL_MIGRATE_CLUSTER = TicketEnumField("MYSQL_MIGRATE_CLUSTER", _("MySQL 克隆主从"), _("集群维护"))
    MYSQL_MASTER_SLAVE_SWITCH = TicketEnumField("MYSQL_MASTER_SLAVE_SWITCH", _("MySQL 主从互换"), _("集群维护"))
    MYSQL_MASTER_FAIL_OVER = TicketEnumField("MYSQL_MASTER_FAIL_OVER", _("MySQL 主库故障切换"), _("集群维护"))
    MYSQL_HA_APPLY = TicketEnumField("MYSQL_HA_APPLY", _("MySQL 高可用部署"), register_iam=False)
    MYSQL_IMPORT_SQLFILE = TicketEnumField("MYSQL_IMPORT_SQLFILE", _("MySQL 变更SQL执行"), _("SQL 任务"))
    MYSQL_SEMANTIC_CHECK = TicketEnumField("MYSQL_SEMANTIC_CHECK", _("MySQL 模拟执行"), register_iam=False)
    MYSQL_PROXY_ADD = TicketEnumField("MYSQL_PROXY_ADD", _("MySQL 添加Proxy"), _("集群维护"))
    MYSQL_PROXY_SWITCH = TicketEnumField("MYSQL_PROXY_SWITCH", _("MySQL 替换Proxy"), _("集群维护"))
    MYSQL_SINGLE_DESTROY = TicketEnumField("MYSQL_SINGLE_DESTROY", _("MySQL 单节点删除"), register_iam=False)
    MYSQL_SINGLE_ENABLE = TicketEnumField("MYSQL_SINGLE_ENABLE", _("MySQL 单节点启用"), register_iam=False)
    MYSQL_SINGLE_DISABLE = TicketEnumField("MYSQL_SINGLE_DISABLE", _("MySQL 单节点禁用"), register_iam=False)
    MYSQL_HA_DESTROY = TicketEnumField("MYSQL_HA_DESTROY", _("MySQL 高可用删除"), register_iam=False)
    MYSQL_HA_DISABLE = TicketEnumField("MYSQL_HA_DISABLE", _("MySQL 高可用禁用"), register_iam=False)
    MYSQL_HA_ENABLE = TicketEnumField("MYSQL_HA_ENABLE", _("MySQL 高可用启用"), register_iam=False)
    MYSQL_AUTHORIZE_RULES = TicketEnumField("MYSQL_AUTHORIZE_RULES", _("MySQL 集群授权"), _("权限管理"))
    MYSQL_EXCEL_AUTHORIZE_RULES = TicketEnumField("MYSQL_EXCEL_AUTHORIZE_RULES", _("MySQL EXCEL授权"), _("权限管理"))
    MYSQL_CLIENT_CLONE_RULES = TicketEnumField("MYSQL_CLIENT_CLONE_RULES", _("MySQL 客户端权限克隆"), register_iam=False)
    MYSQL_INSTANCE_CLONE_RULES = TicketEnumField("MYSQL_INSTANCE_CLONE_RULES", _("MySQL DB实例权限克隆"), _("权限管理"))
    MYSQL_HA_RENAME_DATABASE = TicketEnumField("MYSQL_HA_RENAME_DATABASE", _("MySQL 高可用DB重命名"))
    MYSQL_HA_TRUNCATE_DATA = TicketEnumField("MYSQL_HA_TRUNCATE_DATA", _("MySQL 高可用清档"), _("数据处理"))
    MYSQL_HA_DB_TABLE_BACKUP = TicketEnumField("MYSQL_HA_DB_TABLE_BACKUP", _("MySQL 高可用库表备份"), _("备份"))
    MYSQL_CHECKSUM = TicketEnumField("MYSQL_CHECKSUM", _("MySQL 数据校验修复"), _("数据处理"))
    MYSQL_PARTITION = TicketEnumField("MYSQL_PARTITION", _("MySQL 分区"), _("分区管理"))
    MYSQL_DATA_REPAIR = TicketEnumField("MYSQL_DATA_REPAIR", _("MySQL 数据修复"), register_iam=False)
    MYSQL_FLASHBACK = TicketEnumField("MYSQL_FLASHBACK", _("MySQL 闪回"), _("回档"))
    MYSQL_ROLLBACK_CLUSTER = TicketEnumField("MYSQL_ROLLBACK_CLUSTER", _("MySQL 定点构造"), _("回档"))
    MYSQL_HA_FULL_BACKUP = TicketEnumField("MYSQL_HA_FULL_BACKUP", _("MySQL 高可用全库备份"), _("备份"))
    MYSQL_SINGLE_TRUNCATE_DATA = TicketEnumField("MYSQL_SINGLE_TRUNCATE_DATA", _("MySQL 单节点清档"), register_iam=False)
    MYSQL_SINGLE_RENAME_DATABASE = TicketEnumField("MYSQL_SINGLE_RENAME_DATABASE", _("MySQL 单节点DB重命名"), register_iam=False)
    MYSQL_HA_STANDARDIZE = TicketEnumField("MYSQL_HA_STANDARDIZE", _("TendbHA 标准化"), register_iam=False)
    MYSQL_HA_METADATA_IMPORT = TicketEnumField("MYSQL_HA_METADATA_IMPORT", _("TendbHA 元数据导入"), register_iam=False)
    MYSQL_OPEN_AREA = TicketEnumField("MYSQL_OPEN_AREA", _("MySQL 开区"), _("克隆开区"))

    # SPIDER(TenDB Cluster)
    TENDBCLUSTER_OPEN_AREA = TicketEnumField("TENDBCLUSTER_OPEN_AREA", _("TenDB Cluster 开区"), _("克隆开区"), register_iam=False)
    TENDBCLUSTER_CHECKSUM = TicketEnumField("TENDBCLUSTER_CHECKSUM", _("TenDB Cluster 数据校验修复"), _("数据处理"))
    TENDBCLUSTER_DATA_REPAIR = TicketEnumField("TENDBCLUSTER_DATA_REPAIR", _("TenDB Cluster 数据修复"), register_iam=False)
    TENDBCLUSTER_PARTITION = TicketEnumField("TENDBCLUSTER_PARTITION", _("TenDB Cluster 分区管理"), _("分区管理"))
    TENDBCLUSTER_DB_TABLE_BACKUP = TicketEnumField("TENDBCLUSTER_DB_TABLE_BACKUP", _("TenDB Cluster 库表备份"), _("备份"))
    TENDBCLUSTER_RENAME_DATABASE = TicketEnumField("TENDBCLUSTER_RENAME_DATABASE", _("TenDB Cluster 数据库重命名"), _("SQL 任务"))
    TENDBCLUSTER_TRUNCATE_DATABASE = TicketEnumField("TENDBCLUSTER_TRUNCATE_DATABASE", _("TenDB Cluster 清档"), _("数据处理"))
    TENDBCLUSTER_MASTER_FAIL_OVER = TicketEnumField("TENDBCLUSTER_MASTER_FAIL_OVER", _("TenDB Cluster 主故障切换"), _("集群维护"))
    TENDBCLUSTER_MASTER_SLAVE_SWITCH = TicketEnumField("TENDBCLUSTER_MASTER_SLAVE_SWITCH", _("TenDB Cluster 主从互切"), _("集群维护"))
    TENDBCLUSTER_IMPORT_SQLFILE = TicketEnumField("TENDBCLUSTER_IMPORT_SQLFILE", _("TenDB Cluster 变更SQL执行"), _("SQL 任务"))
    TENDBCLUSTER_SEMANTIC_CHECK = TicketEnumField("TENDBCLUSTER_SEMANTIC_CHECK", _("TenDB Cluster 模拟执行"), register_iam=False)
    TENDBCLUSTER_SPIDER_ADD_NODES = TicketEnumField("TENDBCLUSTER_SPIDER_ADD_NODES", _("TenDB Cluster 扩容接入层"), _("集群维护"))
    TENDBCLUSTER_SPIDER_REDUCE_NODES = TicketEnumField("TENDBCLUSTER_SPIDER_REDUCE_NODES", _("TenDB Cluster 缩容接入层"), _("集群维护"))
    TENDBCLUSTER_SPIDER_MNT_APPLY = TicketEnumField("TENDBCLUSTER_SPIDER_MNT_APPLY", _("TenDB Cluster 添加运维节点"), _("运维 Spider 管理"))  # noqa
    TENDBCLUSTER_SPIDER_MNT_DESTROY = TicketEnumField("TENDBCLUSTER_SPIDER_MNT_DESTROY", _("TenDB Cluster 下架运维节点"), _("运维 Spider 管理"))  # noqa
    TENDBCLUSTER_SPIDER_SLAVE_APPLY = TicketEnumField("TENDBCLUSTER_SPIDER_SLAVE_APPLY", _("TenDB Cluster 部署只读接入层"), _("访问入口"))
    TENDBCLUSTER_SPIDER_SLAVE_DESTROY = TicketEnumField("TENDBCLUSTER_SPIDER_SLAVE_DESTROY", _("TenDB Cluster 只读接入层下架"), _("访问入口"))  # noqa
    TENDBCLUSTER_APPLY = TicketEnumField("TENDBCLUSTER_APPLY", _("TenDB Cluster 集群部署"))
    TENDBCLUSTER_ENABLE = TicketEnumField("TENDBCLUSTER_ENABLE", _("TenDB Cluster 集群启用"), register_iam=False)
    TENDBCLUSTER_DISABLE = TicketEnumField("TENDBCLUSTER_DISABLE", _("TenDB Cluster 集群禁用"), register_iam=False)
    TENDBCLUSTER_DESTROY = TicketEnumField("TENDBCLUSTER_DESTROY", _("TenDB Cluster 集群销毁"), _("集群管理"))
    TENDBCLUSTER_TEMPORARY_DESTROY = TicketEnumField("TENDBCLUSTER_TEMPORARY_DESTROY", _("TenDB Cluster 临时集群销毁"), _("集群管理"))
    TENDBCLUSTER_NODE_REBALANCE = TicketEnumField("TENDBCLUSTER_NODE_REBALANCE", _("TenDB Cluster 集群容量变更"), _("集群维护"))
    TENDBCLUSTER_FULL_BACKUP = TicketEnumField("TENDBCLUSTER_FULL_BACKUP", _("TenDB Cluster 全库备份"), _("备份"))
    TENDBCLUSTER_ROLLBACK_CLUSTER = TicketEnumField("TENDBCLUSTER_ROLLBACK_CLUSTER", _("TenDB Cluster 定点构造"), _("回档"))
    TENDBCLUSTER_FLASHBACK = TicketEnumField("TENDBCLUSTER_FLASHBACK", _("TenDB Cluster 闪回"), _("回档"))
    TENDBCLUSTER_CLIENT_CLONE_RULES = TicketEnumField("TENDBCLUSTER_CLIENT_CLONE_RULES", _("TenDB Cluster 客户端权限克隆"), _("权限管理"))
    TENDBCLUSTER_INSTANCE_CLONE_RULES = TicketEnumField("TENDBCLUSTER_INSTANCE_CLONE_RULES", _("TenDB Cluster DB实例权限克隆"), _("权限管理"))  # noqa
    TENDBCLUSTER_AUTHORIZE_RULES = TicketEnumField("TENDBCLUSTER_AUTHORIZE_RULES", _("TenDB Cluster 授权"), _("权限管理"))
    TENDBCLUSTER_EXCEL_AUTHORIZE_RULES = TicketEnumField("TENDBCLUSTER_EXCEL_AUTHORIZE_RULES", _("TenDB Cluster EXCEL授权"), _("权限管理"))  # noqa
    TENDBCLUSTER_STANDARDIZE = TicketEnumField("TENDBCLUSTER_STANDARDIZE", _("TenDB Cluster 集群标准化"), register_iam=False)
    TENDBCLUSTER_METADATA_IMPORT = TicketEnumField("TENDBCLUSTER_METADATA_IMPORT", _("TenDB Cluster 元数据导入"), register_iam=False)
    TENDBCLUSTER_APPEND_DEPLOY_CTL = TicketEnumField("TENDBCLUSTER_APPEND_DEPLOY_CTL", _("TenDB Cluster 追加部署中控"), register_iam=False)  # noqa
    TENDBSINGLE_METADATA_IMPORT = TicketEnumField("TENDBSINGLE_METADATA_IMPORT", _("TenDB Single 元数据导入"), register_iam=False)
    TENDBSINGLE_STANDARDIZE = TicketEnumField("TENDBSINGLE_STANDARDIZE", _("TenDB Single 集群标准化"), register_iam=False)

    # Tbinlogdumper
    TBINLOGDUMPER_INSTALL = EnumField("TBINLOGDUMPER_INSTALL", _("TBINLOGDUMPER 上架"))
    TBINLOGDUMPER_REDUCE_NODES = EnumField("TBINLOGDUMPER_REDUCE_NODES", _("TBINLOGDUMPER 下架"))
    TBINLOGDUMPER_SWITCH_NODES = EnumField("TBINLOGDUMPER_SWITCH_NODES", _("TBINLOGDUMPER 切换"))
    TBINLOGDUMPER_DISABLE_NODES = EnumField("TBINLOGDUMPER_DISABLE_NODES", _("TBINLOGDUMPER 禁用"))
    TBINLOGDUMPER_ENABLE_NODES = EnumField("TBINLOGDUMPER_ENABLE_NODES", _("TBINLOGDUMPER 启用"))

    # SQLServer
    SQLSERVER_SINGLE_APPLY = TicketEnumField("SQLSERVER_SINGLE_APPLY", _("SQLServer 单节点部署"), register_iam=False)
    SQLSERVER_HA_APPLY = TicketEnumField("SQLSERVER_HA_APPLY", _("SQLServer 高可用部署"), register_iam=False)
    SQLSERVER_IMPORT_SQLFILE = TicketEnumField("SQLSERVER_IMPORT_SQLFILE", _("SQLServer SQL导入执行"), _("变更SQL执行"))
    SQLSERVER_BACKUP_DBS = TicketEnumField("SQLSERVER_BACKUP_DBS", _("SQLServer 库表备份"), _("备份"))
    SQLSERVER_CLEAR_DBS = TicketEnumField("SQLSERVER_CLEAR_DBS", _("SQLServer 清档"), _("数据处理"))
    SQLSERVER_DESTROY = TicketEnumField("SQLSERVER_DESTROY", _("SQLServer 集群卸载"), _("集群管理"))
    SQLSERVER_DISABLE = TicketEnumField("SQLSERVER_DISABLE", _("SQLServer 集群禁用"), register_iam=False)
    SQLSERVER_ENABLE = TicketEnumField("SQLSERVER_ENABLE", _("SQLServer 集群启用"), register_iam=False)
    SQLSERVER_DBRENAME = TicketEnumField("SQLSERVER_DBRENAME", _("SQLServer DB重命名"), _("集群维护"))
    SQLSERVER_MASTER_SLAVE_SWITCH = TicketEnumField("SQLSERVER_MASTER_SLAVE_SWITCH", _("SQLServer 主从互切"), _("集群维护"))
    SQLSERVER_MASTER_FAIL_OVER = TicketEnumField("SQLSERVER_MASTER_FAIL_OVER", _("SQLServer 主故障切换"), _("集群维护"))
    SQLSERVER_RESTORE_LOCAL_SLAVE = TicketEnumField("SQLSERVER_RESTORE_LOCAL_SLAVE", _("SQLServer 原地重建"), _("集群维护"))
    SQLSERVER_RESTORE_SLAVE = TicketEnumField("SQLSERVER_RESTORE_SLAVE", _("SQLServer 新机重建"), _("集群维护"))
    SQLSERVER_ADD_SLAVE = TicketEnumField("SQLSERVER_ADD_SLAVE", _("SQLServer 添加从库"), _("集群维护"))
    SQLSERVER_RESET = TicketEnumField("SQLSERVER_RESET", _("SQLServer 集群重置"), _("集群维护"))
    SQLSERVER_DATA_MIGRATE = TicketEnumField("SQLSERVER_DATA_MIGRATE", _("SQLServer 数据迁移"), _("数据处理"))
    SQLSERVER_ROLLBACK = TicketEnumField("SQLSERVER_ROLLBACK", _("SQLServer 定点构造"), _("数据处理"))
    SQLSERVER_AUTHORIZE_RULES = TicketEnumField("SQLSERVER_AUTHORIZE_RULES", _("SQLServer 集群授权"), _("权限管理"))
    SQLSERVER_EXCEL_AUTHORIZE_RULES = TicketEnumField("SQLSERVER_EXCEL_AUTHORIZE_RULES", _("SQLServer EXCEL授权"), _("权限管理"))

    # REDIS
    REDIS_PLUGIN_CREATE_CLB = TicketEnumField("REDIS_PLUGIN_CREATE_CLB", _("Redis 创建CLB"), _("集群管理"))
    REDIS_PLUGIN_DELETE_CLB = TicketEnumField("REDIS_PLUGIN_DELETE_CLB", _("Redis 删除CLB"), _("集群管理"))
    REDIS_PLUGIN_DNS_BIND_CLB = TicketEnumField("REDIS_PLUGIN_DNS_BIND_CLB", _("Redis 域名绑定CLB"), _("集群管理"))
    REDIS_PLUGIN_DNS_UNBIND_CLB = TicketEnumField("REDIS_PLUGIN_DNS_UNBIND_CLB", _("Redis 域名解绑CLB"), _("集群管理"))
    REDIS_PLUGIN_CREATE_POLARIS = TicketEnumField("REDIS_PLUGIN_CREATE_POLARIS", _("Redis 创建Polaris"), _("集群管理"))
    REDIS_PLUGIN_DELETE_POLARIS = TicketEnumField("REDIS_PLUGIN_DELETE_POLARIS", _("Redis 删除Polaris"), _("集群管理"))
    REDIS_SINGLE_APPLY = TicketEnumField("REDIS_SINGLE_APPLY", _("Redis 单节点部署"), register_iam=False)
    REDIS_INS_APPLY = TicketEnumField("REDIS_INS_APPLY", _("Redis 主从节点部署"), register_iam=False)
    REDIS_CLUSTER_APPLY = TicketEnumField("REDIS_CLUSTER_APPLY", _("Redis 集群部署"), _("集群管理"))
    REDIS_KEYS_EXTRACT = TicketEnumField("REDIS_KEYS_EXTRACT", _("Redis 提取 Key"), _("集群管理"))
    REDIS_KEYS_DELETE = TicketEnumField("REDIS_KEYS_DELETE", _("Redis 删除 key"), _("集群管理"))
    REDIS_BACKUP = TicketEnumField("REDIS_BACKUP", _("Redis 集群备份"), _("集群管理"))
    REDIS_PROXY_OPEN = TicketEnumField("REDIS_PROXY_OPEN", _("Redis 集群启用"), register_iam=False)
    REDIS_PROXY_CLOSE = TicketEnumField("REDIS_PROXY_CLOSE", _("Redis 集群禁用"), register_iam=False)
    REDIS_DESTROY = TicketEnumField("REDIS_DESTROY", _("Redis 集群删除"), _("集群管理"))
    REDIS_PURGE = TicketEnumField("REDIS_PURGE", _("Redis 集群清档"), _("集群管理"))

    REDIS_SCALE_UPDOWN = TicketEnumField("REDIS_SCALE_UPDOWN", _("Redis 集群容量变更"), _("集群维护"))
    REDIS_CLUSTER_CUTOFF = TicketEnumField("REDIS_CLUSTER_CUTOFF", _("Redis 整机替换"), _("集群维护"))
    REDIS_CLUSTER_AUTOFIX = TicketEnumField("REDIS_CLUSTER_AUTOFIX", _("Redis 故障自愈"), _("集群维护"))
    REDIS_CLUSTER_INSTANCE_SHUTDOWN = TicketEnumField("REDIS_CLUSTER_INSTANCE_SHUTDOWN", _("Redis 故障自愈-实例下架"), _("集群维护"))
    REDIS_MASTER_SLAVE_SWITCH = TicketEnumField("REDIS_MASTER_SLAVE_SWITCH", _("Redis 主从切换"), _("集群维护"))
    REDIS_PROXY_SCALE_UP = TicketEnumField("REDIS_PROXY_SCALE_UP", _("Redis Proxy扩容"), _("集群维护"))
    REDIS_PROXY_SCALE_DOWN = TicketEnumField("REDIS_PROXY_SCALE_DOWN", _("Redis Proxy缩容"), _("集群维护"))
    REDIS_ADD_DTS_SERVER = TicketEnumField("REDIS_ADD_DTS_SERVER", _("Redis 新增DTS SERVER"), register_iam=False)
    REDIS_REMOVE_DTS_SERVER = TicketEnumField("REDIS_REMOVE_DTS_SERVER", _("Redis 删除DTS SERVER"), register_iam=False)
    REDIS_DATA_STRUCTURE = TicketEnumField("REDIS_DATA_STRUCTURE", _("Redis 集群数据构造"), _("数据构造"))
    REDIS_DATA_STRUCTURE_TASK_DELETE = TicketEnumField("REDIS_DATA_STRUCTURE_TASK_DELETE", _("Redis 数据构造记录删除"), _("数据构造"))
    REDIS_CLUSTER_SHARD_NUM_UPDATE = TicketEnumField("REDIS_CLUSTER_SHARD_NUM_UPDATE", _("Redis 集群分片数变更"), _("集群维护"))
    REDIS_CLUSTER_TYPE_UPDATE = TicketEnumField("REDIS_CLUSTER_TYPE_UPDATE", _("Redis 集群类型变更"), _("集群维护"))
    REDIS_CLUSTER_DATA_COPY = TicketEnumField("REDIS_CLUSTER_DATA_COPY", _("Redis 集群数据复制"), _("数据传输"))
    REDIS_CLUSTER_ROLLBACK_DATA_COPY = TicketEnumField("REDIS_CLUSTER_ROLLBACK_DATA_COPY", _("Redis 构造实例数据回写"), _("数据构造"))
    REDIS_DATACOPY_CHECK_REPAIR = TicketEnumField("REDIS_DATACOPY_CHECK_REPAIR", _("Redis 数据校验与修复"))
    REDIS_CLUSTER_ADD_SLAVE = TicketEnumField("REDIS_CLUSTER_ADD_SLAVE", _("Redis 新增slave节点"), _("集群维护"))
    REDIS_DTS_ONLINE_SWITCH = TicketEnumField("REDIS_DTS_ONLINE_SWITCH", _("Redis DTS在线切换"), register_iam=False)
    REDIS_TENDIS_META_MITRATE = TicketEnumField("REDIS_TENDIS_META_MITRATE", _("Redis 数据迁移"), register_iam=False)
    REDIS_SLOTS_MIGRATE = TicketEnumField("REDIS_SLOTS_MIGRATE", _("Redis slots 迁移"), register_iam=False)
    REDIS_CLUSTER_VERSION_UPDATE_ONLINE = TicketEnumField("REDIS_CLUSTER_VERSION_UPDATE_ONLINE", _("Redis 集群版本升级"), register_iam=False)  # noqa
    REDIS_CLUSTER_REINSTALL_DBMON = TicketEnumField("REDIS_CLUSTER_REINSTALL_DBMON", _("Redis 集群重装DBMON"), register_iam=False)
    REDIS_PREDIXY_CONFIG_SERVERS_REWRITE = TicketEnumField("REDIS_PREDIXY_CONFIG_SERVERS_REWRITE", _("predixy配置重写"), register_iam=False)  # noqa
    REDIS_CLUSTER_PROXYS_UPGRADE = TicketEnumField("REDIS_CLUSTER_PROXYS_UPGRADE", _("Redis 集群proxys版本升级"), register_iam=False)

    # 大数据
    KAFKA_APPLY = TicketEnumField("KAFKA_APPLY", _("Kafka 集群部署"), register_iam=False)
    KAFKA_SCALE_UP = TicketEnumField("KAFKA_SCALE_UP", _("Kafka 集群扩容"), _("集群管理"))
    KAFKA_SHRINK = TicketEnumField("KAFKA_SHRINK", _("Kafka 集群缩容"), _("集群管理"))
    KAFKA_REBOOT = TicketEnumField("KAFKA_REBOOT", _("Kafka 实例重启"), _("集群管理"))
    KAFKA_REPLACE = TicketEnumField("KAFKA_REPLACE", _("Kafka 集群替换"), _("集群管理"))
    KAFKA_ENABLE = TicketEnumField("KAFKA_ENABLE", _("Kafka 集群启用"), register_iam=False)
    KAFKA_DISABLE = TicketEnumField("KAFKA_DISABLE", _("Kafka 集群禁用"), register_iam=False)
    KAFKA_DESTROY = TicketEnumField("KAFKA_DESTROY", _("Kafka 集群删除"), _("集群管理"))

    HDFS_APPLY = TicketEnumField("HDFS_APPLY", _("HDFS 集群部署"), register_iam=False)
    HDFS_SCALE_UP = TicketEnumField("HDFS_SCALE_UP", _("HDFS 集群扩容"), _("集群管理"))
    HDFS_SHRINK = TicketEnumField("HDFS_SHRINK", _("HDFS 集群缩容"), _("集群管理"))
    HDFS_REBOOT = TicketEnumField("HDFS_REBOOT", _("HDFS 实例重启"), _("集群管理"))
    HDFS_REPLACE = TicketEnumField("HDFS_REPLACE", _("HDFS 集群替换"), _("集群管理"))
    HDFS_ENABLE = TicketEnumField("HDFS_ENABLE", _("HDFS 集群启用"), register_iam=False)
    HDFS_DISABLE = TicketEnumField("HDFS_DISABLE", _("HDFS 集群禁用"), register_iam=False)
    HDFS_DESTROY = TicketEnumField("HDFS_DESTROY", _("HDFS 集群删除"), _("集群管理"))

    ES_APPLY = TicketEnumField("ES_APPLY", _("ES 集群部署"), register_iam=False)
    ES_SCALE_UP = TicketEnumField("ES_SCALE_UP", _("ES 集群扩容"), _("集群管理"))
    ES_SHRINK = TicketEnumField("ES_SHRINK", _("ES 集群缩容"), _("集群管理"))
    ES_REBOOT = TicketEnumField("ES_REBOOT", _("ES 实例重启"), _("集群管理"))
    ES_REPLACE = TicketEnumField("ES_REPLACE", _("ES 集群替换"), _("集群管理"))
    ES_ENABLE = TicketEnumField("ES_ENABLE", _("ES 集群启用"), register_iam=False)
    ES_DISABLE = TicketEnumField("ES_DISABLE", _("ES 集群禁用"), register_iam=False)
    ES_DESTROY = TicketEnumField("ES_DESTROY", _("ES 集群删除"), _("集群管理"))

    PULSAR_APPLY = TicketEnumField("PULSAR_APPLY", _("Pulsar 集群部署"), register_iam=False)
    PULSAR_SCALE_UP = TicketEnumField("PULSAR_SCALE_UP", _("Pulsar 集群扩容"), _("集群管理"))
    PULSAR_SHRINK = TicketEnumField("PULSAR_SHRINK", _("Pulsar 集群缩容"), _("集群管理"))
    PULSAR_REBOOT = TicketEnumField("PULSAR_REBOOT", _("Pulsar 实例重启"), _("集群管理"))
    PULSAR_REPLACE = TicketEnumField("PULSAR_REPLACE", _("Pulsar 集群替换"), _("集群管理"))
    PULSAR_ENABLE = TicketEnumField("PULSAR_ENABLE", _("Pulsar 集群启用"), register_iam=False)
    PULSAR_DISABLE = TicketEnumField("PULSAR_DISABLE", _("Pulsar 集群禁用"), register_iam=False)
    PULSAR_DESTROY = TicketEnumField("PULSAR_DESTROY", _("Pulsar 集群删除"), _("集群管理"))

    INFLUXDB_APPLY = TicketEnumField("INFLUXDB_APPLY", _("InfluxDB 实例部署"), _("实例管理"))
    INFLUXDB_REBOOT = TicketEnumField("INFLUXDB_REBOOT", _("InfluxDB 实例重启"), _("实例管理"))
    INFLUXDB_ENABLE = TicketEnumField("INFLUXDB_ENABLE", _("InfluxDB 实例启用"), register_iam=False)
    INFLUXDB_DISABLE = TicketEnumField("INFLUXDB_DISABLE", _("InfluxDB 实例禁用"), register_iam=False)
    INFLUXDB_DESTROY = TicketEnumField("INFLUXDB_DESTROY", _("InfluxDB 实例删除"), _("实例管理"))
    INFLUXDB_REPLACE = TicketEnumField("INFLUXDB_REPLACE", _("InfluxDB 实例替换"), _("实例管理"))

    # Riak
    RIAK_CLUSTER_APPLY = TicketEnumField("RIAK_CLUSTER_APPLY", _("Riak 集群部署"), register_iam=False)
    RIAK_CLUSTER_SCALE_OUT = TicketEnumField("RIAK_CLUSTER_SCALE_OUT", _("Riak 集群扩容"), _("集群管理"))
    RIAK_CLUSTER_SCALE_IN = TicketEnumField("RIAK_CLUSTER_SCALE_IN", _("Riak 集群缩容"), _("集群管理"))
    RIAK_CLUSTER_DESTROY = TicketEnumField("RIAK_CLUSTER_DESTROY", _("Riak 集群销毁"), _("集群管理"))
    RIAK_CLUSTER_ENABLE = TicketEnumField("RIAK_CLUSTER_ENABLE", _("Riak 集群启用"), register_iam=False)
    RIAK_CLUSTER_DISABLE = TicketEnumField("RIAK_CLUSTER_DISABLE", _("Riak 集群禁用"), register_iam=False)
    RIAK_CLUSTER_REBOOT = TicketEnumField("RIAK_CLUSTER_REBOOT", _("Riak 集群节点重启"), _("集群管理"))
    RIAK_CLUSTER_MIGRATE = TicketEnumField("RIAK_CLUSTER_MIGRATE", _("Riak 集群迁移"), _("集群管理"))

    # MONGODB
    MONGODB_REPLICASET_APPLY = TicketEnumField("MONGODB_REPLICASET_APPLY", _("MongoDB 副本集集群部署"), register_iam=False)
    MONGODB_SHARD_APPLY = TicketEnumField("MONGODB_SHARD_APPLY", _("MongoDB 分片集群部署"), _("集群管理"), register_iam=False)
    MONGODB_EXEC_SCRIPT_APPLY = TicketEnumField("MONGODB_EXEC_SCRIPT_APPLY", _("MongoDB 变更脚本执行"), _("脚本任务"))
    MONGODB_REMOVE_NS = TicketEnumField("MONGODB_REMOVE_NS", _("MongoDB 清档"), _("数据处理"))
    MONGODB_FULL_BACKUP = TicketEnumField("MONGODB_FULL_BACKUP", _("MongoDB 全库备份"), _("备份"))
    MONGODB_BACKUP = TicketEnumField("MONGODB_BACKUP", _("MongoDB 库表备份"), _("备份"))
    MONGODB_ADD_MONGOS = TicketEnumField("MONGODB_ADD_MONGOS", _("MongoDB 扩容接入层"), _("集群维护"))
    MONGODB_REDUCE_MONGOS = TicketEnumField("MONGODB_REDUCE_MONGOS", _("MongoDB 缩容接入层"), _("集群维护"))
    MONGODB_ADD_SHARD_NODES = TicketEnumField("MONGODB_ADD_SHARD_NODES", _("MongoDB 扩容shard节点数"), _("集群维护"))
    MONGODB_REDUCE_SHARD_NODES = TicketEnumField("MONGODB_REDUCE_SHARD_NODES", _("MongoDB 缩容shard节点数"), _("集群维护"))
    MONGODB_SCALE_UPDOWN = TicketEnumField("MONGODB_SCALE_UPDOWN", _("MongoDB 集群容量变更"), _("集群维护"))
    MONGODB_ENABLE = TicketEnumField("MONGODB_ENABLE", _("MongoDB 集群启用"), register_iam=False)
    MONGODB_INSTANCE_RELOAD = TicketEnumField("MONGODB_INSTANCE_RELOAD", _("MongoDB 实例重启"), _("集群管理"))
    MONGODB_DISABLE = TicketEnumField("MONGODB_DISABLE", _("MongoDB 集群禁用"), register_iam=False)
    MONGODB_DESTROY = TicketEnumField("MONGODB_DESTROY", _("MongoDB 集群删除"), _("集群管理"))
    MONGODB_CUTOFF = TicketEnumField("MONGODB_CUTOFF", _("MongoDB 整机替换"), _("集群维护"))
    MONGODB_AUTHORIZE = TicketEnumField("MONGODB_AUTHORIZE", _("MongoDB 授权"), _("权限管理"))
    MONGODB_EXCEL_AUTHORIZE = TicketEnumField("MONGODB_EXCEL_AUTHORIZE", _("MongoDB Excel授权"), _("权限管理"))
    MONGODB_RESTORE = TicketEnumField("MONGODB_RESTORE", _("MongoDB 定点回档"), _("集群维护"))
    MONGODB_TEMPORARY_DESTROY = TicketEnumField("MONGODB_TEMPORARY_DESTROY", _("MongoDB 临时集群销毁"), _("集群维护"))

    # 云区域组件
    CLOUD_SERVICE_APPLY = EnumField("CLOUD_SERVICE_APPLY", _("云区域服务部署"))
    CLOUD_NGINX_APPLY = EnumField("CLOUD_NGINX_APPLY", _("云区域Nginx 服务部署"))
    CLOUD_NGINX_RELOAD = EnumField("CLOUD_NGINX_RELOAD", _("云区域nginx 服务重装"))
    CLOUD_NGINX_REPLACE = EnumField("CLOUD_NGINX_REPLACE", _("云区域nginx 服务替换"))
    CLOUD_DNS_APPLY = EnumField("CLOUD_DNS_APPLY", _("云区域dns 服务部署"))
    CLOUD_DNS_ADD = EnumField("CLOUD_DNS_ADD", _("云区域dns 服务添加"))
    CLOUD_DNS_REDUCE = EnumField("CLOUD_DNS_REDUCE", _("云区域dns 服务裁撤"))
    CLOUD_DNS_REPLACE = EnumField("CLOUD_DNS_REPLACE", _("云区域dns 服务替换"))
    CLOUD_DNS_RELOAD = EnumField("CLOUD_DNS_RELOAD", _("云区域dns 服务重装"))
    CLOUD_DBHA_APPLY = EnumField("CLOUD_DBHA_APPLY", _("云区域dbha 服务部署"))
    CLOUD_DBHA_RELOAD = EnumField("CLOUD_DBHA_RELOAD", _("云区域dbha 服务重装"))
    CLOUD_DBHA_REPLACE = EnumField("CLOUD_DBHA_REPLACE", _("云区域dbha 服务替换"))
    CLOUD_DBHA_ADD = EnumField("CLOUD_DBHA_ADD", _("云区域dbha 服务新增"))
    CLOUD_DBHA_REDUCE = EnumField("CLOUD_DBHA_REDUCE", _("云区域dbha 服务删除"))
    CLOUD_DRS_APPLY = EnumField("CLOUD_DRS_APPLY", _("云区域drs 服务部署"))
    CLOUD_DRS_RELOAD = EnumField("CLOUD_DRS_RELOAD", _("云区域drs 服务重启"))
    CLOUD_DRS_ADD = EnumField("CLOUD_DRS_ADD", _("云区域drs 服务新增"))
    CLOUD_DRS_REDUCE = EnumField("CLOUD_DRS_REDUCE", _("云区域drs 服务删除"))
    CLOUD_DRS_REPLACE = EnumField("CLOUD_DRS_REPLACE", _("云区域drs 服务替换"))
    CLOUD_REDIS_DTS_SERVER_APPLY = EnumField("CLOUD_REDIS_DTS_SERVER_APPLY", _("云区域redis_dts 服务部署"))
    CLOUD_REDIS_DTS_SERVER_ADD = EnumField("CLOUD_REDIS_DTS_SERVER_ADD", _("云区域redis_dts 服务新增"))
    CLOUD_REDIS_DTS_SERVER_REDUCE = EnumField("CLOUD_REDIS_DTS_SERVER_REDUCE", _("云区域redis_dts 服务删除"))

    # 资源池
    RESOURCE_IMPORT = EnumField("RESOURCE_IMPORT", _("资源池导入"))
    # fmt: on


class FlowType(str, StructuredEnum):
    """流程类型枚举"""

    # 蓝鲸ITSM流程服务
    BK_ITSM = EnumField("BK_ITSM", _("单据审批"))
    # 内建执行流程
    INNER_FLOW = EnumField("INNER_FLOW", _("生产部署"))
    # 内建快速执行流程
    QUICK_INNER_FLOW = EnumField("QUICK_INNER_FLOW", _("快速执行"))
    # 内建结果忽略执行流程
    IGNORE_RESULT_INNER_FLOW = EnumField("IGNORE_RESULT_INNER_FLOW", _("结果忽略执行"))
    # 暂停节点
    PAUSE = EnumField("PAUSE", _("人工确认"))
    # 交付节点，仅作为流程结束的标志
    DELIVERY = EnumField("DELIVERY", _("交付"))
    # 描述节点，描述触发创建该单据的任务信息
    DESCRIBE_TASK = EnumField("DESCRIBE_TASK", _("描述任务信息"))
    # 定时节点，用于定时触发单据流程的下一个节点
    TIMER = EnumField("TIMER", _("定时"))
    # 资源申请节点，用于根据资源规格申请对应机器
    RESOURCE_APPLY = EnumField("RESOURCE_APPLY", _("资源申请"))
    # 资源交付节点，用于机器部署成功后通过资源池服务
    RESOURCE_DELIVERY = EnumField("RESOURCE_DELIVERY", _("资源交付"))
    # 资源批量申请节点
    RESOURCE_BATCH_APPLY = EnumField("RESOURCE_BATCH_APPLY", _("资源批量申请"))
    # 资源批量交付节点
    RESOURCE_BATCH_DELIVERY = EnumField("RESOURCE_BATCH_DELIVERY", _("资源批量交付"))


class FlowTypeConfig(str, StructuredEnum):
    """可配置的流程类型枚举。注：请流程触发顺序，倒序定义配置项"""

    # 是否支持人工确认
    NEED_MANUAL_CONFIRM = EnumField("need_manual_confirm", _("人工确认"))
    # 是否支持审批
    NEED_ITSM = EnumField("need_itsm", _("单据审批"))


class FlowCallbackType(str, StructuredEnum):
    """flow钩子工作类型"""

    PRE_CALLBACK = EnumField("pre", _("前置动作"))
    POST_CALLBACK = EnumField("post", _("后继动作"))


class FlowRetryType(str, StructuredEnum):
    """inner flow的重试类型(目前用于互斥执行)"""

    AUTO_RETRY = EnumField("auto_retry", _("自动重试"))
    MANUAL_RETRY = EnumField("manual_retry", _("手动重试"))


class FlowErrCode(int, StructuredEnum):
    """flow的错误代码"""

    GENERAL_ERROR = EnumField(0, _("通用错误代码"))
    AUTO_EXCLUSIVE_ERROR = EnumField(1, _("自动互斥重试错误代码"))
    MANUAL_EXCLUSIVE_ERROR = EnumField(2, _("手动互斥重试错误代码"))

    @classmethod
    def get_err_code(cls, err: Exception, retry_type: str) -> "FlowErrCode":
        # 不是互斥错误，统一认为是其他通用错误
        if not isinstance(err, ClusterExclusiveOperateException):
            return cls.GENERAL_ERROR

        err_code = cls.MANUAL_EXCLUSIVE_ERROR if retry_type == FlowRetryType.MANUAL_RETRY else cls.AUTO_EXCLUSIVE_ERROR
        return err_code


class SwitchConfirmType(str, StructuredEnum):
    """
    切换方式类型
    """

    USER_CONFIRM = EnumField("user_confirm", _("需要人工确认"))
    NO_CONFIRM = EnumField("no_confirm", _("无需确认"))


class SyncDisconnectSettingType(str, StructuredEnum):
    """
    同步断开设置
    """

    AUTO_DISCONNECT = EnumField("auto_disconnect_after_replication", _("数据复制完成后自动断开同步关系"))
    KEEP_SYNC = EnumField("keep_sync_with_reminder", _("数据复制完成后保持同步关系，定时发送断开同步提醒"))


class DataCheckRepairSettingType(str, StructuredEnum):
    """
    数据校验与修复设置
    """

    DATA_CHECK_AND_REPAIR = EnumField("data_check_and_repair", _("数据校验并修复"))
    DATA_CHECK_ONLY = EnumField("data_check_only", _("仅进行数据校验，不进行修复"))
    NO_CHECK_NO_REPAIR = EnumField("no_check_no_repair", _("不校验不修复"))


class RemindFrequencyType(str, StructuredEnum):
    """
    提醒频率
    """

    ONCE_DAILY = EnumField("once_daily", _("一天一次"))
    ONCE_WEEKLY = EnumField("once_weekly", _("一周一次"))


class CheckRepairFrequencyType(str, StructuredEnum):
    """
    校验修复频率
    """

    ONCE_AFTER_REPLICATION = EnumField("once_after_replication", _("一次"))
    ONCE_EVERY_THREE_DAYS = EnumField("once_every_three_days", _("三天一次"))
    ONCE_WEEKLY = EnumField("once_weekly", _("一周一次"))


class WriteModeType(str, StructuredEnum):
    """
    写入方式
    """

    DELETE_WRITE = EnumField("delete_and_write_to_redis", _("删除同名key再写入"))
    APPEND_WRITE = EnumField("keep_and_append_to_redis", _("保留同名key追加写入"))
    FLUSH_WRITE = EnumField("flushall_and_write_to_redis", _("清空集群后写入"))


class TriggerChecksumType(str, StructuredEnum):
    """
    触发数据校验的类型
    """

    NOW = EnumField("now", _("立刻触发"))
    TIMER = EnumField("timer", _("定时触发"))
