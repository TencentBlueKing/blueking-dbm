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
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Dict, List, Union

from django.utils.translation import ugettext as _
from iam import Action

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.exceptions import ActionNotExistError
from backend.ticket.constants import TicketEnumField, TicketType


@dataclass
class ActionMeta(Action):
    """action 属性定义"""

    id: str  # 动作ID
    name: str = ""  # 动作名称
    name_en: str = ""  # 动作英文名称
    type: str = "execute"  # 动作类型
    related_resource_types: List[ResourceMeta] = None  # 关联资源类型
    related_actions: List = None  # 关联动作
    version: str = "1"  # 版本
    group: str = ""  # 动作隶属组
    subgroup: str = ""  # 动作隶属子组

    is_ticket_action: bool = False  # 表示该动作是单据工具箱

    def __post_init__(self):
        super(ActionMeta, self).__init__(id=self.id)
        self.related_actions = self.related_actions or []
        self.related_resource_types = self.related_resource_types or []
        # 单据工具箱初始化
        if self.is_ticket_action:
            self.__ticket_tool_action_init__()

    def __ticket_tool_action_init__(self):
        """单据工具箱action的初始化"""
        ticket_type = self.id.upper()
        group = TicketType.get_db_type_by_ticket(ticket_type)

        self.name = str(TicketType.get_choice_label(ticket_type))
        self.name_en = ticket_type
        self.type = "execute"
        self.related_resource_types = self.related_resource_types or [getattr(ResourceEnum, group.upper())]
        self.related_actions = self.related_actions or []
        self.group = DBType.get_choice_label(group)
        self.subgroup = str(self.subgroup or _("工具箱"))

    def to_json(self):
        content = asdict(self)
        content.pop("is_ticket_action")
        content.update(
            {
                "description": self.name,
                "description_en": self.name_en,
                "related_actions": [action for action in self.related_actions],
                "version": 1,
            }
        )
        related_resource_types = []
        for related_resource in self.related_resource_types:
            related_resource_type = {
                "system_id": related_resource.system_id,
                "id": related_resource.id,
                "selection_mode": related_resource.selection_mode,
            }
            if related_resource.id == ResourceEnum.BUSINESS.id:
                # 如果是biz资源，则依赖cmdb视图
                related_instance_selections = [{"system_id": "bk_cmdb", "id": "business"}]
            else:
                related_instance_selections = [
                    {"system_id": related_resource.system_id, "id": f"{related_resource.select_id}_list"}
                ]
            related_resource_type["related_instance_selections"] = related_instance_selections
            related_resource_types.append(related_resource_type)

        content["related_resource_types"] = related_resource_types
        return content


# fmt: off
class ActionEnum:
    """action 枚举类"""

    DB_MANAGE = ActionMeta(
        id="db_manage",
        name=_("业务访问"),
        name_en="DB Manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("业务"),
    )

    GLOBAL_MANAGE = ActionMeta(
        id="global_manage",
        name=_("平台管理访问"),
        name_en="Global Manage",
        type="manage",
        related_actions=[],
        related_resource_types=[],
        group=_("平台管理"),
        subgroup=_(""),
    )

    TICKET_VIEW = ActionMeta(
        id="ticket_view",
        name=_("单据查看"),
        name_en="ticket_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("业务"),
        subgroup=_(""),
    )

    RESOURCE_MANAGE = ActionMeta(
        id="resource_manage",
        name=_("资源管理访问"),
        name_en="resource_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[],
        group=_("资源管理"),
        subgroup=_(""),
    )

    FLOW_DETAIL = ActionMeta(
        id="flow_detail",
        name=_("任务流程详情"),
        name_en="Flow Detail",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.TASKFLOW],
        group=_("业务"),
        subgroup=_("历史任务"),
    )

    MYSQL_APPLY = ActionMeta(
        id="mysql_apply",
        name=_("MySQL 部署"),
        name_en="MySQL Apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MySQL"),
        subgroup=_("集群管理"),
    )

    MYSQL_VIEW = ActionMeta(
        id="mysql_view",
        name=_("MySQL 集群详情查看"),
        name_en="MySQL View",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("集群管理"),
    )

    MYSQL_ENABLE_DISABLE = ActionMeta(
        id="mysql_enable_disable",
        name=_("MySQL 集群禁用和启用"),
        name_en="MySQL Enable Disable",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("集群管理"),
    )

    MYSQL_CLIENT_CLONE_RULES = ActionMeta(
        id="mysql_client_clone_rules",
        name=_("MySQL 客户端克隆"),
        name_en="mysql_client_clone_rules",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MySQL"),
        subgroup=_("集群管理"),
    )

    MYSQL_DESTROY = ActionMeta(
        id="mysql_destroy",
        name=_("MySQL 集群删除"),
        name_en="MySQL Destroy",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("集群管理"),
    )

    MYSQL_CREATE_ACCOUNT = ActionMeta(
        id="mysql_account_create",
        name=_("MySQL 账号创建"),
        name_en="MySQL Account Create",
        type="create",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MySQL"),
        subgroup=_("权限管理"),
    )

    MYSQL_DELETE_ACCOUNT = ActionMeta(
        id="mysql_account_delete",
        name=_("MySQL 账号删除"),
        name_en="MySQL Account Delete",
        type="delete",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MySQL"),
        subgroup=_("权限管理"),
    )

    MYSQL_ADD_ACCOUNT_RULE = ActionMeta(
        id="mysql_account_rule_create",
        name=_("MySQL 账号规则创建"),
        name_en="MySQL Account Rule Create",
        type="create",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MySQL"),
        subgroup=_("权限管理"),
    )

    MYSQL_EXCEL_AUTHORIZE_RULES = ActionMeta(
        id=TicketType.MYSQL_EXCEL_AUTHORIZE_RULES.lower(),
        related_resource_types=[ResourceEnum.BUSINESS],
        subgroup=_("权限管理"),
        is_ticket_action=True
    )

    MYSQL_PARTITION_CREATE = ActionMeta(
        id="mysql_partition_create",
        name=_("MySQL 分区管理创建"),
        name_en="mysql_partition_create",
        type="create",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MySQL"),
        subgroup=_("分区管理"),
    )

    MYSQL_PARTITION_UPDATE = ActionMeta(
        id="mysql_partition_update",
        name=_("MySQL 分区管理更新"),
        name_en="mysql_partition_update",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MySQL"),
        subgroup=_("分区管理"),
    )

    MYSQL_PARTITION_DELETE = ActionMeta(
        id="mysql_partition_delete",
        name=_("MySQL 分区管理删除"),
        name_en="mysql_partition_delete",
        type="delete",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MySQL"),
        subgroup=_("分区管理"),
    )

    MYSQL_PARTITION_ENABLE_DISABLE = ActionMeta(
        id="mysql_partition_enable_disable",
        name=_("MySQL 分区管理禁用启用"),
        name_en="mysql_partition_enable_disable",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MySQL"),
        subgroup=_("分区管理"),
    )

    MYSQL_OPENAREA_CONFIG_CREATE = ActionMeta(
        id="mysql_openarea_config_create",
        name=_("MySQL 开区模板创建"),
        name_en="mysql_openarea_config_create",
        type="create",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MySQL"),
        subgroup=_("克隆开区"),
    )

    MYSQL_OPENAREA_CONFIG_UPDATE = ActionMeta(
        id="mysql_openarea_config_update",
        name=_("MySQL 开区模板编辑"),
        name_en="mysql_openarea_config_edit",
        type="edit",
        related_actions=[],
        related_resource_types=[ResourceEnum.OPENAREA_CONFIG],
        group=_("MySQL"),
        subgroup=_("克隆开区"),
    )

    MYSQL_OPENAREA_CONFIG_DESTROY = ActionMeta(
        id="mysql_openarea_config_destroy",
        name=_("MySQL 开区模板删除"),
        name_en="mysql_openarea_config_delete",
        type="delete",
        related_actions=[],
        related_resource_types=[ResourceEnum.OPENAREA_CONFIG],
        group=_("MySQL"),
        subgroup=_("克隆开区"),
    )

    DUMPER_CONFIG_VIEW = ActionMeta(
        id="dumper_config_view",
        name=_("Dumper 订阅规则详情查看"),
        name_en="dumper_config_view",
        type="view",
        related_actions=[],
        related_resource_types=[ResourceEnum.DUMPER_SUBSCRIBE_CONFIG],
        group=_("MySQL"),
        subgroup=_("Dumper管理"),
    )

    DUMPER_CONFIG_UPDATE = ActionMeta(
        id="dumper_config_update",
        name=_("Dumper 订阅规则编辑"),
        name_en="dumper_config_update",
        type="edit",
        related_actions=[DUMPER_CONFIG_VIEW.id],
        related_resource_types=[ResourceEnum.DUMPER_SUBSCRIBE_CONFIG],
        group=_("MySQL"),
        subgroup=_("Dumper管理"),
    )

    DUMPER_CONFIG_DESTROY = ActionMeta(
        id="dumper_config_destroy",
        name=_("Dumper 订阅规则删除"),
        name_en="dumper_config_destroy",
        type="delete",
        related_actions=[DUMPER_CONFIG_VIEW.id],
        related_resource_types=[ResourceEnum.DUMPER_SUBSCRIBE_CONFIG],
        group=_("MySQL"),
        subgroup=_("Dumper管理"),
    )

    TBINLOGDUMPER_INSTALL = ActionMeta(
        id="tbinlogdumper_install",
        name=_("Dumper 实例创建"),
        name_en="tbinlogdumper_install",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("Dumper管理"),
    )

    TBINLOGDUMPER_ENABLE_DISABLE = ActionMeta(
        id="tbinlogdumper_enable_disable",
        name=_("Dumper 实例禁用与启用"),
        name_en="tbinlogdumper_enable_disable",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("Dumper管理"),
    )

    TBINLOGDUMPER_SWITCH_NODES = ActionMeta(
        id="tbinlogdumper_switch_nodes",
        name=_("Dumper 实例迁移"),
        name_en="tbinlogdumper_switch_nodes",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("Dumper管理"),
    )

    TBINLOGDUMPER_REDUCE_NODES = ActionMeta(
        id="tbinlogdumper_reduce_nodes",
        name=_("Dumper 实例删除"),
        name_en="tbinlogdumper_reduce_nodes",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("Dumper管理"),
    )

    TENDBCLUSTER_VIEW = ActionMeta(
        id="tendbcluster_view",
        name=_("TendbCluster 集群查看"),
        name_en="tendbcluster_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("集群管理"),
    )

    TENDBCLUSTER_CREATE_ACCOUNT = ActionMeta(
        id="tendbcluster_account_create",
        name=_("TendbCluster 账号创建"),
        name_en="tendbcluster_account_create",
        type="create",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("TendbCluster"),
        subgroup=_("权限管理"),
    )

    TENDBCLUSTER_DELETE_ACCOUNT = ActionMeta(
        id="tendbcluster_account_delete",
        name=_("TendbCluster 账号删除"),
        name_en="tendbcluster_account_delete",
        type="delete",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("TendbCluster"),
        subgroup=_("权限管理"),
    )

    TENDBCLUSTER_ADD_ACCOUNT_RULE = ActionMeta(
        id="tendbcluster_add_account_rule",
        name=_("TendbCluster 账号规则创建"),
        name_en="tendbcluster_add_account_rule",
        type="create",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("TendbCluster"),
        subgroup=_("权限管理"),
    )

    TENDBCLUSTER_EXCEL_AUTHORIZE_RULES = ActionMeta(
        id="tendb_excel_authorize_rules",
        name=_("TendbCluster Excel授权"),
        name_en="tendb_excel_authorize_rules",
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("TendbCluster"),
        subgroup=_("权限管理"),
    )

    TENDBCLUSTER_CLIENT_CLONE_RULES = ActionMeta(
        id="tendb_cluster_client_clone_rules",
        name=_("TendbCluster 客户端克隆权限"),
        name_en="tendb_cluster_client_clone_rules",
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("TendbCluster"),
        subgroup=_("权限管理"),
    )

    TENDBCLUSTER_INSTANCE_CLONE_RULES = ActionMeta(
        id="tendb_instance_clone_rules",
        name=_("TendbCluster DB实例权限克隆"),
        name_en="tendb_instance_clone_rules",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("权限克隆"),
    )

    TENDBCLUSTER_OPENAREA_CONFIG_CREATE = ActionMeta(
        id="tendb_openarea_config_create",
        name=_("TendbCluster 开区模板创建"),
        name_en="tendbcluster_openarea_config_create",
        type="create",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("TendbCluster"),
        subgroup=_("克隆开区"),
    )

    TENDBCLUSTER_OPENAREA_CONFIG_UPDATE = ActionMeta(
        id="tendb_openarea_config_update",
        name=_("TendbCluster 开区模板编辑"),
        name_en="tendbcluster_openarea_config_edit",
        type="edit",
        related_actions=[],
        related_resource_types=[ResourceEnum.OPENAREA_CONFIG],
        group=_("TendbCluster"),
        subgroup=_("克隆开区"),
    )

    TENDBCLUSTER_OPENAREA_CONFIG_DESTROY = ActionMeta(
        id="tendb_openarea_config_destroy",
        name=_("TendbCluster 开区模板删除"),
        name_en="tendbcluster_openarea_config_delete",
        type="delete",
        related_actions=[],
        related_resource_types=[ResourceEnum.OPENAREA_CONFIG],
        group=_("TendbCluster"),
        subgroup=_("克隆开区"),
    )

    TENDBCLUSTER_PARTITION_CREATE = ActionMeta(
        id="tendbcluster_partition_create",
        name=_("TendbCLuster 分区管理创建"),
        name_en="tendbcluster_partition_create",
        type="create",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("TendbCluster"),
        subgroup=_("分区管理"),
    )

    TENDBCLUSTER_PARTITION_UPDATE = ActionMeta(
        id="tendbcluster_partition_update",
        name=_("TendbCluster 分区管理更新"),
        name_en="tendbcluster_partition_update",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("TendbCluster"),
        subgroup=_("分区管理"),
    )

    TENDBCLUSTER_PARTITION_DELETE = ActionMeta(
        id="tendbcluster_partition_delete",
        name=_("TendbCluster 分区管理删除"),
        name_en="tendbcluster_partition_delete",
        type="delete",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("TendbCluster"),
        subgroup=_("分区管理"),
    )

    TENDBCLUSTER_PARTITION_ENABLE_DISABLE = ActionMeta(
        id="tendb_partition_enable_disable",
        name=_("TendbCluster 分区管理禁用启用"),
        name_en="tendb_partition_enable_disable",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("TendbCluster"),
        subgroup=_("分区管理"),
    )

    TENDBCLUSTER_APPLY = ActionMeta(
        id=TicketType.TENDBCLUSTER_APPLY.lower(),
        related_resource_types=[ResourceEnum.BUSINESS],
        subgroup=_("集群管理"),
        is_ticket_action=True
    )

    TENDBCLUSTER_ENABLE_DISABLE = ActionMeta(
        id="tendbcluster_enable_disable",
        name=_("TendbCluster 集群禁用启用"),
        name_en="tendbcluster_enable_disable",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("集群管理"),
    )

    TENDBCLUSTER_SPIDER_SLAVE_DESTROY = ActionMeta(
        id="tendb_spider_slave_destroy",
        name=_("TendbCluster 下架只读接入层"),
        name_en="tendb_spider_slave_destroy",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("访问入口"),
    )

    REDIS_VIEW = ActionMeta(
        id="redis_view",
        name=_("Redis 集群详情查看"),
        name_en="redis_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
    )

    REDIS_OPEN_CLOSE = ActionMeta(
        id="redis_open_close",
        name=_("Redis 集群禁用启用"),
        name_en="redis_open_close",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
    )

    INFLUXDB_APPLY = ActionMeta(
        id=TicketType.INFLUXDB_APPLY.lower(),
        related_resource_types=[ResourceEnum.BUSINESS],
        subgroup=_("实例管理"),
        is_ticket_action=True
    )

    INFLUXDB_VIEW = ActionMeta(
        id="influxdb_view",
        name=_("InfluxDB 实例查看"),
        name_en="influxdb_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.INFLUXDB],
        group=_("InfluxDB"),
        subgroup=_("实例管理"),
    )

    INFLUXDB_ENABLE_DISABLE = ActionMeta(
        id="influxdb_enable_disable",
        name=_("InfluxDB 实例禁用启用"),
        name_en="influxdb_enable_disable",
        type="execute",
        related_actions=[INFLUXDB_VIEW.id],
        related_resource_types=[ResourceEnum.INFLUXDB],
        group=_("InfluxDB"),
        subgroup=_("实例管理"),
    )

    ES_APPLY = ActionMeta(
        id="es_apply",
        name=_("ES 集群部署"),
        name_en="es_apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("ES"),
        subgroup=_("集群管理"),
    )

    ES_VIEW = ActionMeta(
        id="es_view",
        name=_("ES 集群详情查看"),
        name_en="es_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.ES],
        group=_("ES"),
        subgroup=_("集群管理"),
    )

    ES_ENABLE_DISABLE = ActionMeta(
        id="es_enable_disable",
        name=_("ES 集群禁用启用"),
        name_en="es_enable_disable",
        type="execute",
        related_actions=[ES_VIEW.id],
        related_resource_types=[ResourceEnum.ES],
        group=_("ES"),
        subgroup=_("集群管理"),
    )

    KAFKA_VIEW = ActionMeta(
        id="kafka_view",
        name=_("Kafka 集群详情查看"),
        name_en="kafka_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.KAFKA],
        group=_("Kafka"),
        subgroup=_("集群管理"),
    )

    KAFKA_APPLY = ActionMeta(
        id=TicketType.KAFKA_APPLY.lower(),
        related_resource_types=[ResourceEnum.BUSINESS],
        subgroup=_("集群管理"),
        is_ticket_action=True
    )

    KAFKA_ENABLE_DISABLE = ActionMeta(
        id="kafka_enable_disable",
        name=_("Kafka 集群禁用启用"),
        name_en="kafka_enable_disable",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.KAFKA],
        group=_("Kafka"),
        subgroup=_("集群管理"),
    )

    HDFS_APPLY = ActionMeta(
        id=TicketType.HDFS_APPLY.lower(),
        related_resource_types=[ResourceEnum.BUSINESS],
        subgroup=_("集群管理"),
        is_ticket_action=True
    )

    HDFS_VIEW = ActionMeta(
        id="hdfs_view",
        name=_("HDFS 集群详情查看"),
        name_en="hdfs_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.HDFS],
        group=_("HDFS"),
        subgroup=_("集群管理"),
    )

    HDFS_ENABLE_DISABLE = ActionMeta(
        id="hdfs_enable_disable",
        name=_("HDFS 集群禁用启用"),
        name_en="hdfs_enable_disable",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.HDFS],
        group=_("HDFS"),
        subgroup=_("集群管理"),
    )

    PULSAR_APPLY = ActionMeta(
        id=TicketType.PULSAR_APPLY.lower(),
        related_resource_types=[ResourceEnum.BUSINESS],
        subgroup=_("集群管理"),
        is_ticket_action=True
    )

    PULSAR_VIEW = ActionMeta(
        id="pulsar_view",
        name=_("Pulsar 集群详情查看"),
        name_en="pulsar_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.PULSAR],
        group=_("Pulsar"),
        subgroup=_("集群管理"),
    )

    PULSAR_ENABLE_DISABLE = ActionMeta(
        id="pulsar_enable_disable",
        name=_("Pulsar 集群禁用启用"),
        name_en="pulsar_enable_disable",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.PULSAR],
        group=_("Pulsar"),
        subgroup=_("集群管理"),
    )

    RIAK_CLUSTER_APPLY = ActionMeta(
        id=TicketType.RIAK_CLUSTER_APPLY.lower(),
        related_resource_types=[ResourceEnum.BUSINESS],
        subgroup=_("集群管理"),
        is_ticket_action=True
    )

    RIAK_VIEW = ActionMeta(
        id="riak_view",
        name=_("Riak 集群详情查看"),
        name_en="riak_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.RIAK],
        group=_("Riak"),
        subgroup=_("集群管理"),
    )

    RIAK_ENABLE_DISABLE = ActionMeta(
        id="riak_enable_disable",
        name=_("Riak 集群禁用启用"),
        name_en="riak_enable_disable",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.RIAK],
        group=_("Riak"),
        subgroup=_("集群管理"),
    )

    MONGODB_VIEW = ActionMeta(
        id="mongodb_view",
        name=_("Mongodb 集群详情查看"),
        name_en="mongodb_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MONGODB],
        group=_("MongoDB"),
        subgroup=_("集群管理"),
    )

    MONGODB_APPLY = ActionMeta(
        id="mongodb_apply",
        name=_("MongoDB 部署"),
        name_en="mongodb_apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MongoDB"),
        subgroup=_("集群管理"),
    )

    MONGODB_ENABLE_DISABLE = ActionMeta(
        id="mongodb_enable_disable",
        name=_("MongoDB 集群禁用启用"),
        name_en="mongodb_enable_disable",
        type="execute",
        related_actions=[MONGODB_VIEW.id],
        related_resource_types=[ResourceEnum.MONGODB],
        group=_("MongoDB"),
        subgroup=_("集群管理"),
    )

    MONGODB_CREATE_ACCOUNT = ActionMeta(
        id="mongodb_account_create",
        name=_("MongoDB 账号创建"),
        name_en="mongodb_account_create",
        type="create",
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MongoDB"),
        subgroup=_("权限管理"),
    )

    MONGODB_DELETE_ACCOUNT = ActionMeta(
        id="mongodb_delete_create",
        name=_("MongoDB 账号删除"),
        name_en="mongodb_delete_create",
        type="delete",
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MongoDB"),
        subgroup=_("权限管理"),
    )

    MONGODB_ADD_ACCOUNT_RULE = ActionMeta(
        id="mongodb_add_account_rule",
        name=_("MongoDB 账号规则创建"),
        name_en="mongodb_add_account_rule",
        type="create",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MongoDB"),
        subgroup=_("权限管理"),
    )

    SQLSERVER_VIEW = ActionMeta(
        id="sqlserver_view",
        name=_("SQLServer 集群详情查看"),
        name_en="sqlserver_view",
        type="view",
        related_resource_types=[ResourceEnum.SQLSERVER],
        group=_("SQLServer"),
        subgroup=_("集群管理"),
    )

    SQLSERVER_APPLY = ActionMeta(
        id="sqlserver_apply",
        name=_("SQLServer 部署"),
        name_en="sqlserver_apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("SQLServer"),
        subgroup=_("集群管理"),
    )

    SQLSERVER_CREATE_ACCOUNT = ActionMeta(
        id="sqlserver_account_create",
        name=_("SQLServer 账号创建"),
        name_en="sqlserver_account_create",
        type="create",
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("SQLServer"),
        subgroup=_("权限管理"),
    )

    SQLSERVER_DELETE_ACCOUNT = ActionMeta(
        id="sqlserver_delete_create",
        name=_("SQLServer 账号删除"),
        name_en="sqlserver_delete_create",
        type="delete",
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("SQLServer"),
        subgroup=_("权限管理"),
    )

    SQLSERVER_ADD_ACCOUNT_RULE = ActionMeta(
        id="sqlserver_add_account_rule",
        name=_("SQLServer 账号规则创建"),
        name_en="sqlserver_add_account_rule",
        type="create",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("SQLServer"),
        subgroup=_("权限管理"),
    )

    SQLSERVER_ENABLE_DISABLE = ActionMeta(
        id="sqlserver_enable_disable",
        name=_("SQLServer 集群禁用和启用"),
        name_en="sqlserver_enable_disable",
        type="execute",
        related_actions=[SQLSERVER_VIEW.id],
        related_resource_types=[ResourceEnum.SQLSERVER],
        group=_("SQLServer"),
        subgroup=_("集群管理"),
    )

    RESOURCE_POLL_MANAGE = ActionMeta(
        id="resource_pool_manage",
        name=_("资源池管理"),
        name_en="resource_pool_manage",
        type="manage",
        related_actions=[RESOURCE_MANAGE.id],
        related_resource_types=[],
        group=_("资源管理"),
        subgroup=_("资源池"),
    )

    DIRTY_POLL_MANAGE = ActionMeta(
        id="dirty_pool_manage",
        name=_("污点池管理"),
        name_en="dirty_pool_manage",
        type="manage",
        related_actions=[RESOURCE_MANAGE.id],
        related_resource_types=[],
        group=_("资源管理"),
        subgroup=_("污点池"),
    )

    HEALTHY_REPORT_VIEW = ActionMeta(
        id="health_report_view",
        name=_("健康报告查看"),
        name_en="health_report_view",
        type="view",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("平台管理"),
    )

    DBHA_SWITCH_EVENT_VIEW = ActionMeta(
        id="dbha_switch_event_view",
        name=_("DBHA切换事件查看"),
        name_en="dbha_switch_event_view",
        type="view",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("平台管理"),
    )

    NOTIFY_GROUP_LIST = ActionMeta(
        id="notify_group_list",
        name=_("告警组查看"),
        name_en="notify_group_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("配置管理"),
        subgroup=_("告警组"),
    )

    GLOBAL_NOTIFY_GROUP_LIST = ActionMeta(
        id="global_notify_group_list",
        name=_("全局告警组查看"),
        name_en="global_notify_group_view",
        type="view",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[],
        group=_("平台管理"),
        subgroup=_("告警组"),
    )

    NOTIFY_GROUP_CREATE = ActionMeta(
        id="notify_group_create",
        name=_("告警组新建"),
        name_en="notify_group_create",
        type="create",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("配置管理"),
        subgroup=_("告警组"),
    )

    GLOBAL_NOTIFY_GROUP_CREATE = ActionMeta(
        id="global_notify_group_create",
        name=_("全局告警组新建"),
        name_en="global_notify_group_create",
        type="create",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[],
        group=_("平台管理"),
        subgroup=_("告警组"),
    )

    NOTIFY_GROUP_UPDATE = ActionMeta(
        id="notify_group_update",
        name=_("告警组编辑"),
        name_en="notify_group_edit",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("配置管理"),
        subgroup=_("告警组"),
    )

    GLOBAL_NOTIFY_GROUP_UPDATE = ActionMeta(
        id="global_notify_group_update",
        name=_("全局告警组编辑"),
        name_en="global_notify_group_edit",
        type="manage",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[],
        group=_("平台管理"),
        subgroup=_("告警组"),
    )

    NOTIFY_GROUP_DESTROY = ActionMeta(
        id="notify_group_delete",
        name=_("告警组删除"),
        name_en="notify_group_delete",
        type="delete",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("配置管理"),
        subgroup=_("告警组"),
    )

    GLOBAL_NOTIFY_GROUP_DESTROY = ActionMeta(
        id="global_notify_group_delete",
        name=_("全局告警组删除"),
        name_en="global_notify_group_delete",
        type="delete",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[],
        group=_("平台管理"),
        subgroup=_("告警组"),
    )

    MONITOR_POLICY_LIST = ActionMeta(
        id="monitor_policy_view",
        name=_("监控策略查看"),
        name_en="monitor_policy_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS, ResourceEnum.DBTYPE],
        group=_("配置管理"),
        subgroup=_("监控策略"),
    )

    GLOBAL_MONITOR_POLICY_LIST = ActionMeta(
        id="global_monitor_policy_view",
        name=_("全局监控策略查看"),
        name_en="global_monitor_policy_view",
        type="view",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("平台管理"),
        subgroup=_("监控策略"),
    )

    MONITOR_POLICY_UPDATE_STRATEGY = ActionMeta(
        id="monitor_policy_edit",
        name=_("监控策略编辑"),
        name_en="monitor_policy_edit",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MONITOR_POLICY],
        group=_("配置管理"),
        subgroup=_("监控策略"),
    )

    GLOBAL_MONITOR_POLICY_UPDATE_STRATEGY = ActionMeta(
        id="global_monitor_policy_edit",
        name=_("全局监控策略编辑"),
        name_en="global_monitor_policy_edit",
        type="manage",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[ResourceEnum.GLOBAL_MONITOR_POLICY],
        group=_("平台管理"),
        subgroup=_("监控策略"),
    )

    MONITOR_POLICY_DESTROY = ActionMeta(
        id="monitor_policy_delete",
        name=_("监控策略删除"),
        name_en="monitor_policy_delete",
        type="delete",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MONITOR_POLICY],
        group=_("配置管理"),
        subgroup=_("监控策略"),
    )

    MONITOR_POLICY_ENABLE_DISABLE = ActionMeta(
        id="monitor_policy_start_stop",
        name=_("监控策略启停"),
        name_en="monitor_policy_start_stop",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MONITOR_POLICY],
        group=_("配置管理"),
        subgroup=_("监控策略"),
    )

    GLOBAL_MONITOR_POLICY_ENABLE_DISABLE = ActionMeta(
        id="global_monitor_policy_start_stop",
        name=_("全局监控策略启停"),
        name_en="global_monitor_policy_start_stop",
        type="manage",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[ResourceEnum.GLOBAL_MONITOR_POLICY],
        group=_("平台管理"),
        subgroup=_("监控策略"),
    )

    MONITOR_POLICY_ALARM_VIEW = ActionMeta(
        id="monitor_policy_alarm_view",
        name=_("监控告警查看"),
        name_en="monitor_policy_alarm_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MONITOR_POLICY],
        group=_("配置管理"),
        subgroup=_("监控策略"),
    )

    MONITOR_POLICY_CLONE_STRATEGY = ActionMeta(
        id="monitor_policy_clone",
        name=_("监控策略克隆"),
        name_en="monitor_policy_clone",
        type="create",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MONITOR_POLICY],
        group=_("配置管理"),
        subgroup=_("监控策略"),
    )

    DBCONFIG_VIEW = ActionMeta(
        id="dbconfig_view",
        name=_("数据库配置查看"),
        name_en="dbconfig_view",
        type="view",
        related_actions=[],
        related_resource_types=[ResourceEnum.BUSINESS, ResourceEnum.DBTYPE],
        group=_("配置管理"),
        subgroup=_("数据库配置"),
    )

    DBCONFIG_EDIT = ActionMeta(
        id="dbconfig_edit",
        name=_("数据库配置编辑"),
        name_en="dbconfig_edit",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.BUSINESS, ResourceEnum.DBTYPE],
        group=_("配置管理"),
        subgroup=_("数据库配置"),
    )

    GLOBAL_DBCONFIG_VIEW = ActionMeta(
        id="global_dbconfig_view",
        name=_("全局数据库配置查看"),
        name_en="global_dbconfig_view",
        type="view",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("平台管理"),
        subgroup=_("数据库配置"),
    )

    GLOBAL_DBCONFIG_EDIT = ActionMeta(
        id="global_dbconfig_edit",
        name=_("全局数据库配置编辑"),
        name_en="global_dbconfig_edit",
        type="manage",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("平台管理"),
        subgroup=_("数据库配置"),
    )

    GLOBAL_DBCONFIG_CREATE = ActionMeta(
        id="global_dbconfig_create",
        name=_("全局数据库配置新增"),
        name_en="global_dbconfig_create",
        type="create",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("平台管理"),
        subgroup=_("数据库配置"),
    )

    GLOBAL_DBCONFIG_DESTROY = ActionMeta(
        id="global_dbconfig_destroy",
        name=_("全局数据库配置删除"),
        name_en="global_dbconfig_destroy",
        type="delete",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("平台管理"),
        subgroup=_("数据库配置"),
    )

    DBA_ADMINISTRATOR_EDIT = ActionMeta(
        id="dba_administrator_edit",
        name=_("DBA人员设置"),
        name_en="dba_administrator_edit",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("配置管理"),
        subgroup=_(""),
    )

    GLOBAL_DBA_ADMINISTRATOR_EDIT = ActionMeta(
        id="global_dba_administrator_edit",
        name=_("全局DBA人员设置"),
        name_en="global_dba_administrator_edit",
        type="manage",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[],
        group=_("平台管理"),
        subgroup=_(""),
    )

    PACKAGE_VIEW = ActionMeta(
        id="package_view",
        name=_("版本文件查看"),
        name_en="package_view",
        type="view",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("平台管理"),
        subgroup=_("版本文件"),
    )

    PACKAGE_MANAGE = ActionMeta(
        id="package_manage",
        name=_("版本文件管理"),
        name_en="package_manage",
        type="manage",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("平台管理"),
        subgroup=_("版本文件"),
    )

    PASSWORD_POLICY_SET = ActionMeta(
        id="password_policy_set",
        name=_("密码安全规则设置"),
        name_en="password_policy_set",
        type="manage",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[],
        group=_("平台管理"),
        subgroup=_(""),
    )

    SPEC_CREATE = ActionMeta(
        id="spec_create",
        name=_("资源规格新建"),
        name_en="spec_create",
        type="create",
        related_actions=[RESOURCE_MANAGE.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("资源管理"),
        subgroup=_("资源规格"),
    )

    SPEC_UPDATE = ActionMeta(
        id="spec_update",
        name=_("资源规格编辑"),
        name_en="spec_update",
        type="manage",
        related_actions=[RESOURCE_MANAGE.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("资源管理"),
        subgroup=_("资源规格"),
    )

    SPEC_DESTROY = ActionMeta(
        id="spec_delete",
        name=_("资源规格删除"),
        name_en="spec_delete",
        type="delete",
        related_actions=[RESOURCE_MANAGE.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("资源管理"),
        subgroup=_("资源规格"),
    )

    DUTY_RULE_LIST = ActionMeta(
        id="duty_rule_list",
        name=_("轮值策略查看"),
        name_en="duty_rule_list",
        type="view",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("平台管理"),
        subgroup=_("轮值策略"),
    )

    DUTY_RULE_CREATE = ActionMeta(
        id="duty_rule_create",
        name=_("轮值策略新增"),
        name_en="duty_rule_create",
        type="create",
        related_actions=[GLOBAL_MANAGE.id, DUTY_RULE_LIST.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("平台管理"),
        subgroup=_("轮值策略"),
    )

    DUTY_RULE_UPDATE = ActionMeta(
        id="duty_rule_update",
        name=_("轮值策略编辑"),
        name_en="duty_rule_update",
        type="manage",
        related_actions=[GLOBAL_MANAGE.id, DUTY_RULE_LIST.id],
        related_resource_types=[ResourceEnum.DUTY_RULE],
        group=_("平台管理"),
        subgroup=_("轮值策略"),
    )

    DUTY_RULE_DESTROY = ActionMeta(
        id="duty_rule_destroy",
        name=_("轮值策略删除"),
        name_en="duty_rule_destroy",
        type="delete",
        related_actions=[GLOBAL_MANAGE.id, DUTY_RULE_LIST.id],
        related_resource_types=[ResourceEnum.DUTY_RULE],
        group=_("平台管理"),
        subgroup=_("轮值策略"),
    )

    IP_WHITELIST_MANAGE = ActionMeta(
        id="ip_whitelist_manage",
        name=_("授权白名单管理"),
        name_en="ip_whitelist_manage",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("配置管理"),
        subgroup=_(""),
    )

    GLOBAL_IP_WHITELIST_MANAGE = ActionMeta(
        id="global_ip_whitelist_manage",
        name=_("全局授权白名单管理"),
        name_en="global_ip_whitelist_manage",
        type="manage",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[],
        group=_("平台管理"),
        subgroup=_(""),
    )

    UPDATE_DUTY_NOTICE_CONFIG = ActionMeta(
        id="update_duty_notices_config",
        name=_("轮值通知设置"),
        name_en="update_duty_notices_config",
        type="manage",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[],
        group=_("平台管理"),
        subgroup=_("轮值策略"),
    )

    ACCESS_ENTRY_EDIT = ActionMeta(
        id="access_entry_edit",
        name=_("集群入口访问修改"),
        name_en="access_entry_edit",
        type="edit",
        related_actions=[],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("平台管理"),
    )

    @classmethod
    def get_action_by_id(cls, action_id: Union[(ActionMeta, str)]) -> ActionMeta:
        if isinstance(action_id, ActionMeta):
            return action_id
        if action_id in cls.__dict__:
            return cls.__dict__[action_id]
        if action_id in _all_actions:
            return _all_actions[action_id]

        raise ActionNotExistError(_("动作ID不存在: {}").format(action_id))

    @classmethod
    def cluster_type_to_view(cls, cluster_type):
        """集群类型与集群详情操作的映射"""
        db_type = ClusterType.cluster_type_to_db_type(cluster_type)
        return getattr(cls, f"{db_type.upper()}_VIEW")

    @classmethod
    def instance_type_to_instance_action(cls, instance_role):
        """实例类型与实例详情动作的映射"""
        if instance_role == InstanceRole.INFLUXDB:
            return cls.INFLUXDB_VIEW

    @classmethod
    def get_actions_by_resource(cls, resource_id):
        """获取操作资源对应的操作类型"""
        if getattr(cls, "action_sets_map", None):
            return cls.action_sets_map[resource_id]

        action_sets_map: Dict[str, List] = defaultdict(list)
        for action in cls.__dict__.values():
            if not isinstance(action, ActionMeta):
                continue
            for resource in action.related_resource_types:
                action_sets_map[resource.id].append(action)

        cls.action_sets_map = action_sets_map
        return cls.action_sets_map[resource_id]

    @classmethod
    def get_match_actions(cls, name, exclude=None):
        """通过名字模糊匹配动作列表"""
        exclude = exclude or []
        actions = [
            action
            for action in cls.__dict__.values()
            if isinstance(action, ActionMeta) and name in action.id and action not in exclude
        ]
        return actions


# fmt: on
def register_ticket_iam_actions():
    """ 将单据动作注册到IAM动作类中"""
    for ticket_type in TicketType.get_values():
        ticket_enum = TicketType.__field_members__[ticket_type]
        # 如果单据类型要求不注册iam，则忽略
        if not isinstance(ticket_enum, TicketEnumField) or not ticket_enum.register_iam:
            continue

        ticket_action = ActionMeta(id=ticket_type.lower(), subgroup=ticket_enum.subgroup, is_ticket_action=True)
        # 优先以定义为准，否则自动注册
        if not getattr(ActionEnum, ticket_type.upper(), None):
            setattr(ActionEnum, ticket_type.upper(), ticket_action)


register_ticket_iam_actions()

_all_actions = {action.id: action for action in ActionEnum.__dict__.values() if isinstance(action, ActionMeta)}
