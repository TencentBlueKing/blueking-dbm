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

from django.utils.translation import ugettext_lazy as _

from backend.configuration.constants import DBType
from backend.db_meta.exceptions import ClusterExclusiveOperateException
from backend.flow.consts import StateType
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


class TicketFlowStatus(str, StructuredEnum):
    """单据流程状态枚举类"""

    PENDING = EnumField("PENDING", _("等待中"))
    RUNNING = EnumField("RUNNING", _("执行中"))
    SUCCEEDED = EnumField("SUCCEEDED", _("成功"))
    FAILED = EnumField("FAILED", _("失败"))
    REVOKED = EnumField("REVOKED", _("撤销"))
    SKIPPED = EnumField("SKIPPED", _("跳过"))


FLOW_FINISHED_STATUS = [TicketFlowStatus.SKIPPED, TicketStatus.SUCCEEDED]
FLOW_NOT_EXECUTE_STATUS = [TicketFlowStatus.SKIPPED, TicketStatus.PENDING]

BAMBOO_STATE__TICKET_STATE_MAP = {
    StateType.FINISHED.value: TicketFlowStatus.SUCCEEDED.value,
    StateType.FAILED.value: TicketFlowStatus.FAILED.value,
    StateType.REVOKED.value: TicketFlowStatus.REVOKED.value,
    StateType.RUNNING.value: TicketFlowStatus.RUNNING.value,
}

EXCLUSIVE_TICKET_EXCEL_PATH = "backend/ticket/exclusive_ticket.xlsx"


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
        if db_type == DBType.Redis.upper():
            ticket_types.extend([cls.TENDIS_META_MITRATE.value, cls.PROXY_SCALE_UP, cls.PROXY_SCALE_DOWN])
        elif db_type == DBType.TenDBCluster.upper():
            ticket_types.append(cls.MYSQL_PARTITION)
        return ticket_types

    # MYSQL
    MYSQL_SINGLE_APPLY = EnumField("MYSQL_SINGLE_APPLY", _("MySQL 单节点部署"))
    MYSQL_ADD_SLAVE = EnumField("MYSQL_ADD_SLAVE", _("MySQL 添加从库"))
    MYSQL_RESTORE_SLAVE = EnumField("MYSQL_RESTORE_SLAVE", _("MySQL Slave重建"))
    MYSQL_RESTORE_LOCAL_SLAVE = EnumField("MYSQL_RESTORE_LOCAL_SLAVE", _("MySQL Slave原地重建"))
    MYSQL_MIGRATE_CLUSTER = EnumField("MYSQL_MIGRATE_CLUSTER", _("MySQL 克隆主从"))
    MYSQL_MASTER_SLAVE_SWITCH = EnumField("MYSQL_MASTER_SLAVE_SWITCH", _("MySQL 主从互换"))
    MYSQL_MASTER_FAIL_OVER = EnumField("MYSQL_MASTER_FAIL_OVER", _("MySQL 主库故障切换"))
    MYSQL_HA_APPLY = EnumField("MYSQL_HA_APPLY", _("MySQL 高可用部署"))
    MYSQL_IMPORT_SQLFILE = EnumField("MYSQL_IMPORT_SQLFILE", _("MySQL 变更SQL执行"))
    MYSQL_SEMANTIC_CHECK = EnumField("MYSQL_SEMANTIC_CHECK", _("MySQL 模拟执行"))
    MYSQL_PROXY_ADD = EnumField("MYSQL_PROXY_ADD", _("MySQL 添加Proxy"))
    MYSQL_PROXY_SWITCH = EnumField("MYSQL_PROXY_SWITCH", _("MySQL 替换Proxy"))
    MYSQL_SINGLE_DESTROY = EnumField("MYSQL_SINGLE_DESTROY", _("MySQL 单节点删除"))
    MYSQL_SINGLE_ENABLE = EnumField("MYSQL_SINGLE_ENABLE", _("MySQL 单节点启用"))
    MYSQL_SINGLE_DISABLE = EnumField("MYSQL_SINGLE_DISABLE", _("MySQL 单节点禁用"))
    MYSQL_HA_DESTROY = EnumField("MYSQL_HA_DESTROY", _("MySQL 高可用删除"))
    MYSQL_HA_DISABLE = EnumField("MYSQL_HA_DISABLE", _("MySQL 高可用禁用"))
    MYSQL_HA_ENABLE = EnumField("MYSQL_HA_ENABLE", _("MySQL 高可用启用"))
    MYSQL_AUTHORIZE_RULES = EnumField("MYSQL_AUTHORIZE_RULES", _("MySQL 授权"))
    MYSQL_EXCEL_AUTHORIZE_RULES = EnumField("MYSQL_EXCEL_AUTHORIZE_RULES", _("MySQL EXCEL-授权"))
    MYSQL_CLIENT_CLONE_RULES = EnumField("MYSQL_CLIENT_CLONE_RULES", _("MySQL 客户端权限克隆"))
    MYSQL_INSTANCE_CLONE_RULES = EnumField("MYSQL_INSTANCE_CLONE_RULES", _("MySQL DB实例权限克隆"))
    MYSQL_HA_RENAME_DATABASE = EnumField("MYSQL_HA_RENAME_DATABASE", _("MySQL 高可用DB重命名"))
    MYSQL_HA_TRUNCATE_DATA = EnumField("MYSQL_HA_TRUNCATE_DATA", _("MySQL 高可用清档"))
    MYSQL_HA_DB_TABLE_BACKUP = EnumField("MYSQL_HA_DB_TABLE_BACKUP", _("MySQL 高可用库表备份"))
    MYSQL_CHECKSUM = EnumField("MYSQL_CHECKSUM", _("MySQL 数据校验修复"))
    MYSQL_PARTITION = EnumField("MYSQL_PARTITION", _("MySQL 分区"))
    MYSQL_DATA_REPAIR = EnumField("MYSQL_DATA_REPAIR", _("MySQL 数据修复"))
    MYSQL_FLASHBACK = EnumField("MYSQL_FLASHBACK", _("MySQL 闪回"))
    MYSQL_ROLLBACK_CLUSTER = EnumField("MYSQL_ROLLBACK_CLUSTER", _("MySQL 定点构造"))
    MYSQL_HA_FULL_BACKUP = EnumField("MYSQL_HA_FULL_BACKUP", _("MySQL 高可用全库备份"))
    MYSQL_SINGLE_TRUNCATE_DATA = EnumField("MYSQL_SINGLE_TRUNCATE_DATA", _("MySQL 单节点清档"))
    MYSQL_SINGLE_RENAME_DATABASE = EnumField("MYSQL_SINGLE_RENAME_DATABASE", _("MySQL 单节点DB重命名"))
    MYSQL_HA_STANDARDIZE = EnumField("MYSQL_HA_STANDARDIZE", _("TendbHA 标准化"))
    MYSQL_HA_METADATA_IMPORT = EnumField("MYSQL_HA_METADATA_IMPORT", _("TendbHA 元数据导入"))
    MYSQL_OPEN_AREA = EnumField("MYSQL_OPEN_AREA", _("MySQL 开区"))

    # SPIDER(TenDB Cluster)
    TENDBCLUSTER_CHECKSUM = EnumField("TENDBCLUSTER_CHECKSUM", _("TenDB Cluster 数据校验修复"))
    TENDBCLUSTER_DATA_REPAIR = EnumField("TENDBCLUSTER_DATA_REPAIR", _("TenDB Cluster 数据修复"))
    TENDBCLUSTER_PARTITION = EnumField("TENDBCLUSTER_PARTITION", _("TenDB Cluster 分区管理"))
    TENDBCLUSTER_DB_TABLE_BACKUP = EnumField("TENDBCLUSTER_DB_TABLE_BACKUP", _("TenDB Cluster 库表备份"))
    TENDBCLUSTER_RENAME_DATABASE = EnumField("TENDBCLUSTER_RENAME_DATABASE", _("TenDB Cluster 数据库重命名"))
    TENDBCLUSTER_TRUNCATE_DATABASE = EnumField("TENDBCLUSTER_TRUNCATE_DATABASE", _("TenDB Cluster 清档"))
    TENDBCLUSTER_MASTER_FAIL_OVER = EnumField("TENDBCLUSTER_MASTER_FAIL_OVER", _("TenDB Cluster 主故障切换"))
    TENDBCLUSTER_MASTER_SLAVE_SWITCH = EnumField("TENDBCLUSTER_MASTER_SLAVE_SWITCH", _("TenDB Cluster 主从互切"))
    TENDBCLUSTER_IMPORT_SQLFILE = EnumField("TENDBCLUSTER_IMPORT_SQLFILE", _("TenDB Cluster 变更SQL执行"))
    TENDBCLUSTER_SEMANTIC_CHECK = EnumField("TENDBCLUSTER_SEMANTIC_CHECK", _("TenDB Cluster 模拟执行"))
    TENDBCLUSTER_SPIDER_ADD_NODES = EnumField("TENDBCLUSTER_SPIDER_ADD_NODES", _("TenDB Cluster 扩容接入层"))
    TENDBCLUSTER_SPIDER_REDUCE_NODES = EnumField("TENDBCLUSTER_SPIDER_REDUCE_NODES", _("TenDB Cluster 缩容接入层"))
    TENDBCLUSTER_SPIDER_MNT_APPLY = EnumField("TENDBCLUSTER_SPIDER_MNT_APPLY", _("TenDB Cluster 添加运维节点"))
    TENDBCLUSTER_SPIDER_MNT_DESTROY = EnumField("TENDBCLUSTER_SPIDER_MNT_DESTROY", _("TenDB Cluster 下架运维节点"))
    TENDBCLUSTER_SPIDER_SLAVE_APPLY = EnumField("TENDBCLUSTER_SPIDER_SLAVE_APPLY", _("TenDB Cluster 部署只读接入层"))
    TENDBCLUSTER_SPIDER_SLAVE_DESTROY = EnumField("TENDBCLUSTER_SPIDER_SLAVE_DESTROY", _("TenDB Cluster 只读接入层下架"))
    TENDBCLUSTER_APPLY = EnumField("TENDBCLUSTER_APPLY", _("TenDB Cluster 集群部署"))
    TENDBCLUSTER_ENABLE = EnumField("TENDBCLUSTER_ENABLE", _("TenDB Cluster 集群启用"))
    TENDBCLUSTER_DISABLE = EnumField("TENDBCLUSTER_DISABLE", _("TenDB Cluster 集群禁用"))
    TENDBCLUSTER_DESTROY = EnumField("TENDBCLUSTER_DESTROY", _("TenDB Cluster 集群销毁"))
    TENDBCLUSTER_TEMPORARY_DESTROY = EnumField("TENDBCLUSTER_TEMPORARY_DESTROY", _("TenDB Cluster 临时集群销毁"))
    TENDBCLUSTER_NODE_REBALANCE = EnumField("TENDBCLUSTER_NODE_REBALANCE", _("TenDB Cluster 集群容量变更"))
    TENDBCLUSTER_FULL_BACKUP = EnumField("TENDBCLUSTER_FULL_BACKUP", _("TenDB Cluster 全库备份"))
    TENDBCLUSTER_ROLLBACK_CLUSTER = EnumField("TENDBCLUSTER_ROLLBACK_CLUSTER", _("TenDB Cluster 定点构造"))
    TENDBCLUSTER_FLASHBACK = EnumField("TENDBCLUSTER_FLASHBACK", _("TenDB Cluster 闪回"))
    TENDBCLUSTER_CLIENT_CLONE_RULES = EnumField("TENDBCLUSTER_CLIENT_CLONE_RULES", _("TenDB Cluster 客户端权限克隆"))
    TENDBCLUSTER_INSTANCE_CLONE_RULES = EnumField("TENDBCLUSTER_INSTANCE_CLONE_RULES", _("TenDB Cluster DB实例权限克隆"))
    TENDBCLUSTER_AUTHORIZE_RULES = EnumField("TENDBCLUSTER_AUTHORIZE_RULES", _("TenDB Cluster 授权"))
    TENDBCLUSTER_EXCEL_AUTHORIZE_RULES = EnumField("TENDBCLUSTER_EXCEL_AUTHORIZE_RULES", _("TenDB Cluster EXCEL-授权"))

    # Tbinlogdumper
    TBINLOGDUMPER_INSTALL = EnumField("TBINLOGDUMPER_INSTALL", _("TBINLOGDUMPER 上架"))
    TBINLOGDUMPER_REDUCE_NODES = EnumField("TBINLOGDUMPER_REDUCE_NODES", _("TBINLOGDUMPER 下架"))
    TBINLOGDUMPER_SWITCH_NODES = EnumField("TBINLOGDUMPER_SWITCH_NODES", _("TBINLOGDUMPER 切换"))
    TBINLOGDUMPER_DISABLE_NODES = EnumField("TBINLOGDUMPER_DISABLE_NODES", _("TBINLOGDUMPER 禁用"))
    TBINLOGDUMPER_ENABLE_NODES = EnumField("TBINLOGDUMPER_ENABLE_NODES", _("TBINLOGDUMPER 启用"))

    # REDIS
    REDIS_PLUGIN_CREATE_CLB = EnumField("REDIS_PLUGIN_CREATE_CLB", _("Redis 创建CLB"))
    REDIS_PLUGIN_DELETE_CLB = EnumField("REDIS_PLUGIN_DELETE_CLB", _("Redis 删除CLB"))
    REDIS_PLUGIN_DNS_BIND_CLB = EnumField("REDIS_PLUGIN_DNS_BIND_CLB", _("Redis 域名绑定CLB"))
    REDIS_PLUGIN_DNS_UNBIND_CLB = EnumField("REDIS_PLUGIN_DNS_UNBIND_CLB", _("Redis 域名解绑CLB"))
    REDIS_PLUGIN_CREATE_POLARIS = EnumField("REDIS_PLUGIN_CREATE_POLARIS", _("Redis 创建Polaris"))
    REDIS_PLUGIN_DELETE_POLARIS = EnumField("REDIS_PLUGIN_DELETE_POLARIS", _("Redis 删除Polaris"))
    REDIS_SINGLE_APPLY = EnumField("REDIS_SINGLE_APPLY", _("Redis 单节点部署"))
    REDIS_CLUSTER_APPLY = EnumField("REDIS_CLUSTER_APPLY", _("Redis 集群部署"))
    REDIS_KEYS_EXTRACT = EnumField("REDIS_KEYS_EXTRACT", _("Redis 提取 Key"))
    REDIS_KEYS_DELETE = EnumField("REDIS_KEYS_DELETE", _("Redis 删除 key"))
    REDIS_BACKUP = EnumField("REDIS_BACKUP", _("Redis 集群备份"))
    REDIS_OPEN = EnumField("REDIS_PROXY_OPEN", _("Redis 集群启用"))
    REDIS_CLOSE = EnumField("REDIS_PROXY_CLOSE", _("Redis 集群禁用"))
    REDIS_DESTROY = EnumField("REDIS_DESTROY", _("Redis 集群删除"))
    REDIS_PURGE = EnumField("REDIS_PURGE", _("Redis 集群清档"))

    REDIS_SCALE_UPDOWN = EnumField("REDIS_SCALE_UPDOWN", _("Redis 集群容量变更"))
    REDIS_CLUSTER_CUTOFF = EnumField("REDIS_CLUSTER_CUTOFF", _("Redis 整机替换"))
    REDIS_CLUSTER_AUTOFIX = EnumField("REDIS_CLUSTER_AUTOFIX", _("Redis 故障自愈"))
    REDIS_CLUSTER_INSTANCE_SHUTDOWN = EnumField("REDIS_CLUSTER_INSTANCE_SHUTDOWN", _("Redis 故障自愈-实例下架"))
    REDIS_MASTER_SLAVE_SWITCH = EnumField("REDIS_MASTER_SLAVE_SWITCH", _("Redis 主从切换"))
    PROXY_SCALE_UP = EnumField("PROXY_SCALE_UP", _("Redis Proxy扩容"))
    PROXY_SCALE_DOWN = EnumField("PROXY_SCALE_DOWN", _("Redis Proxy缩容"))
    REDIS_ADD_DTS_SERVER = EnumField("REDIS_ADD_DTS_SERVER", _("Redis 新增DTS SERVER"))
    REDIS_REMOVE_DTS_SERVER = EnumField("REDIS_REMOVE_DTS_SERVER", _("Redis 删除DTS SERVER"))
    REDIS_DATA_STRUCTURE = EnumField("REDIS_DATA_STRUCTURE", _("Redis 集群数据构造"))
    REDIS_DATA_STRUCTURE_TASK_DELETE = EnumField("REDIS_DATA_STRUCTURE_TASK_DELETE", _("Redis 数据构造记录删除"))
    REDIS_CLUSTER_SHARD_NUM_UPDATE = EnumField("REDIS_CLUSTER_SHARD_NUM_UPDATE", _("Redis 集群分片数变更"))
    REDIS_CLUSTER_TYPE_UPDATE = EnumField("REDIS_CLUSTER_TYPE_UPDATE", _("Redis 集群类型变更"))
    REDIS_CLUSTER_DATA_COPY = EnumField("REDIS_CLUSTER_DATA_COPY", _("Redis 集群数据复制"))
    REDIS_CLUSTER_ROLLBACK_DATA_COPY = EnumField("REDIS_CLUSTER_ROLLBACK_DATA_COPY", _("Redis 构造实例数据回写"))
    REDIS_DATACOPY_CHECK_REPAIR = EnumField("REDIS_DATACOPY_CHECK_REPAIR", _("Redis 数据校验与修复"))
    REDIS_CLUSTER_ADD_SLAVE = EnumField("REDIS_CLUSTER_ADD_SLAVE", _("Redis 新增slave节点"))
    REDIS_DTS_ONLINE_SWITCH = EnumField("REDIS_DTS_ONLINE_SWITCH", _("Redis DTS在线切换"))
    TENDIS_META_MITRATE = EnumField("TENDIS_META_MITRATE", _("Redis 数据迁移"))
    REDIS_SLOTS_MIGRATE = EnumField("REDIS_SLOTS_MIGRATE", _("Redis slots 迁移"))
    REDIS_CLUSTER_VERSION_UPDATE_ONLINE = EnumField("REDIS_CLUSTER_VERSION_UPDATE_ONLINE", _("Redis 集群版本升级"))

    # 大数据
    KAFKA_APPLY = EnumField("KAFKA_APPLY", _("Kafka 集群部署"))
    KAFKA_SCALE_UP = EnumField("KAFKA_SCALE_UP", _("Kafka 集群扩容"))
    KAFKA_SHRINK = EnumField("KAFKA_SHRINK", _("Kafka 集群缩容"))
    KAFKA_REBOOT = EnumField("KAFKA_REBOOT", _("Kafka 实例重启"))
    KAFKA_REPLACE = EnumField("KAFKA_REPLACE", _("Kafka 集群替换"))
    KAFKA_ENABLE = EnumField("KAFKA_ENABLE", _("Kafka 集群启用"))
    KAFKA_DISABLE = EnumField("KAFKA_DISABLE", _("Kafka 集群禁用"))
    KAFKA_DESTROY = EnumField("KAFKA_DESTROY", _("Kafka 集群删除"))

    HDFS_APPLY = EnumField("HDFS_APPLY", _("HDFS 集群部署"))
    HDFS_SCALE_UP = EnumField("HDFS_SCALE_UP", _("HDFS 集群扩容"))
    HDFS_SHRINK = EnumField("HDFS_SHRINK", _("HDFS 集群缩容"))
    HDFS_REBOOT = EnumField("HDFS_REBOOT", _("HDFS 实例重启"))
    HDFS_REPLACE = EnumField("HDFS_REPLACE", _("HDFS 集群替换"))
    HDFS_ENABLE = EnumField("HDFS_ENABLE", _("HDFS 集群启用"))
    HDFS_DISABLE = EnumField("HDFS_DISABLE", _("HDFS 集群禁用"))
    HDFS_DESTROY = EnumField("HDFS_DESTROY", _("HDFS 集群删除"))

    ES_APPLY = EnumField("ES_APPLY", _("ES 集群部署"))
    ES_SCALE_UP = EnumField("ES_SCALE_UP", _("ES 集群扩容"))
    ES_SHRINK = EnumField("ES_SHRINK", _("ES 集群缩容"))
    ES_REBOOT = EnumField("ES_REBOOT", _("ES 实例重启"))
    ES_REPLACE = EnumField("ES_REPLACE", _("ES 集群替换"))
    ES_ENABLE = EnumField("ES_ENABLE", _("ES 集群启用"))
    ES_DISABLE = EnumField("ES_DISABLE", _("ES 集群禁用"))
    ES_DESTROY = EnumField("ES_DESTROY", _("ES 集群删除"))

    PULSAR_APPLY = EnumField("PULSAR_APPLY", _("Pulsar 集群部署"))
    PULSAR_SCALE_UP = EnumField("PULSAR_SCALE_UP", _("Pulsar 集群扩容"))
    PULSAR_SHRINK = EnumField("PULSAR_SHRINK", _("Pulsar 集群缩容"))
    PULSAR_REBOOT = EnumField("PULSAR_REBOOT", _("Pulsar 实例重启"))
    PULSAR_REPLACE = EnumField("PULSAR_REPLACE", _("Pulsar 集群替换"))
    PULSAR_ENABLE = EnumField("PULSAR_ENABLE", _("Pulsar 集群启用"))
    PULSAR_DISABLE = EnumField("PULSAR_DISABLE", _("Pulsar 集群禁用"))
    PULSAR_DESTROY = EnumField("PULSAR_DESTROY", _("Pulsar 集群删除"))

    INFLUXDB_APPLY = EnumField("INFLUXDB_APPLY", _("InfluxDB 实例部署"))
    INFLUXDB_REBOOT = EnumField("INFLUXDB_REBOOT", _("InfluxDB 实例重启"))
    INFLUXDB_ENABLE = EnumField("INFLUXDB_ENABLE", _("InfluxDB 实例启用"))
    INFLUXDB_DISABLE = EnumField("INFLUXDB_DISABLE", _("InfluxDB 实例禁用"))
    INFLUXDB_DESTROY = EnumField("INFLUXDB_DESTROY", _("InfluxDB 实例删除"))
    INFLUXDB_REPLACE = EnumField("INFLUXDB_REPLACE", _("InfluxDB 实例替换"))

    # Riak
    RIAK_CLUSTER_APPLY = EnumField("RIAK_CLUSTER_APPLY", _("RIAK 集群部署"))
    RIAK_CLUSTER_SCALE_OUT = EnumField("RIAK_CLUSTER_SCALE_OUT", _("RIAK 集群扩容"))
    RIAK_CLUSTER_SCALE_IN = EnumField("RIAK_CLUSTER_SCALE_IN", _("RIAK 集群缩容"))
    RIAK_CLUSTER_DESTROY = EnumField("RIAK_CLUSTER_DESTROY", _("RIAK 集群销毁"))
    RIAK_CLUSTER_ENABLE = EnumField("RIAK_CLUSTER_ENABLE", _("RIAK集群启用"))
    RIAK_CLUSTER_DISABLE = EnumField("RIAK_CLUSTER_DISABLE", _("RIAK集群禁用"))
    RIAK_CLUSTER_REBOOT = EnumField("RIAK_CLUSTER_REBOOT", _("RIAK集群节点重启"))

    # MONGODB
    MONGODB_REPLICASET_APPLY = EnumField("MONGODB_REPLICASET_APPLY", _("RIAK 集群部署"))

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
