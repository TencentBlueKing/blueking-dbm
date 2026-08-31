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

from django.utils.translation import gettext as _
from iam import Action

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.iam_app.constans import MAX_ACTION_NAME_LEN, CommonActionLabel
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.exceptions import ActionNotExistError, BaseIAMError
from backend.ticket.constants import TicketEnumField, TicketType


@dataclass
class ActionMeta(Action):
    """action 属性定义"""

    id: str  # 动作ID
    name: str = ""  # 动作名称
    name_en: str = ""  # 动作英文名称
    description: str = ""  # 动作描述
    description_en: str = ""  # 动作英文描述
    type: str = "execute"  # 动作类型
    related_resource_types: List[ResourceMeta] = None  # 关联资源类型
    related_actions: List = None  # 关联动作
    version: str = "1"  # 版本
    hidden: bool = False  # 是否隐藏(隐藏后不允许在iam页面申请该动作)
    group: str = ""  # 动作隶属组
    subgroup: str = ""  # 动作隶属子组
    common_labels: List[str] = None  # 动作隶属常用操作配置组

    is_ticket_action: bool = False  # 表示该动作是单据工具箱

    def __post_init__(self):
        super(ActionMeta, self).__init__(id=self.id)
        # 如果单据长度大于32，则报错
        if len(self.id) > MAX_ACTION_NAME_LEN:
            raise BaseIAMError(_("动作ID{}长度超过{}，无法注册iam，请重新命名").format(self.id, MAX_ACTION_NAME_LEN))
        self.related_actions = self.related_actions or []
        self.related_resource_types = self.related_resource_types or []
        self.common_labels = self.common_labels or []
        # 单据工具箱初始化
        if self.is_ticket_action:
            self.__ticket_tool_action_init__()

    def __ticket_tool_action_init__(self):
        """单据工具箱action的初始化"""
        ticket_type = self.id.upper()
        group = TicketType.get_db_type_by_ticket(ticket_type)
        # 单据动作基础定义
        self.name = str(TicketType.get_choice_label(ticket_type))
        self.name_en = ticket_type
        self.type = "execute"
        # 单据动作关联资源默认是group资源
        self.related_resource_types = self.related_resource_types or [getattr(ResourceEnum, group.upper())]
        self.related_actions = self.related_actions or []
        # 添加单据动作所属组和常用操作
        self.group = DBType.get_choice_label(group)
        self.subgroup = str(self.subgroup or _("工具箱"))

    def to_json(self):
        content = asdict(self)
        content.pop("is_ticket_action")
        content.pop("common_labels")
        content.update(
            {
                "description": self.description or self.name,
                "description_en": self.description_en or self.description or self.name_en,
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

    def __hash__(self):
        return hash((self.id, self.name))

    def __eq__(self, other):
        if not isinstance(other, ActionMeta):
            return False
        return other.id == self.id


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
        common_labels=[
            CommonActionLabel.BIZ_READ_ONLY,
            CommonActionLabel.BIZ_MAINTAIN,
            CommonActionLabel.DEVELOPER,
            CommonActionLabel.MYSQL_AUTHORIZE_RULES,
            CommonActionLabel.MYSQL_IMPORT_SQLFILE,
            CommonActionLabel.TENDBCLUSTER_AUTHORIZE_RULES,
            CommonActionLabel.TENDBCLUSTER_IMPORT_SQLFILE,
            CommonActionLabel.EXTERNAL_DEVELOPER,
        ],
    )

    GLOBAL_MANAGE = ActionMeta(
        id="global_manage",
        name=_("全局设置访问"),
        name_en="Global Manage",
        type="manage",
        related_actions=[],
        related_resource_types=[],
        group=_("全局设置"),
        subgroup="",
        hidden=True,
    )

    TICKET_VIEW = ActionMeta(
        id="ticket_view",
        name=_("单据查看"),
        name_en="ticket_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.TICKET],
        group=_("业务"),
        subgroup=_("单据"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    GLOBAL_TICKET_CONFIG_SET = ActionMeta(
        id="ticket_config_set",
        name=_("全局单据流程设置"),
        name_en="ticket_config_set",
        type="edit",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("全局设置"),
        hidden=True,
    )

    BIZ_TICKET_CONFIG_SET = ActionMeta(
        id="biz_ticket_config_set",
        name=_("单据审批设置"),
        name_en="biz_ticket_config_set",
        type="edit",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS, ResourceEnum.DBTYPE],
        group=_("业务"),
        subgroup=_("业务配置"),
    )

    BIZ_ASSISTANCE_VARS_CONFIG = ActionMeta(
        id="biz_assistance_vars_config",
        name=_("单据协助设置"),
        name_en="biz_assistance_vars_config",
        type="edit",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("业务"),
        subgroup=_("业务配置"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    BIZ_NOTIFY_CONFIG = ActionMeta(
        id="biz_notify_config",
        name=_("单据通知设置"),
        name_en="biz_notify_config",
        type="edit",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("业务"),
        subgroup=_("业务配置"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    RESOURCE_MANAGE = ActionMeta(
        id="resource_manage",
        name=_("资源管理访问"),
        name_en="resource_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[],
        group=_("资源管理"),
        subgroup="",
        hidden=True,
    )

    FLOW_DETAIL = ActionMeta(
        id="flow_detail",
        name=_("任务流程管理"),
        name_en="Flow Detail",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.TASKFLOW],
        group=_("业务"),
        subgroup=_("单据"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    PLATFORM_MANAGE = ActionMeta(
        id="platform_manage",
        name=_("平台管理"),
        name_en="platform_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[],
        group=_("平台管理"),
        subgroup="",
        common_labels=[],
    )

    PLATFORM_TICKET_VIEW = ActionMeta(
        id="platform_ticket_view",
        name=_("全局单据查看"),
        name_en="platform_ticket_view",
        type="manage",
        related_actions=[],
        related_resource_types=[],
        group=_("平台管理"),
        subgroup="",
        common_labels=[],
    )

    PLATFORM_TASKFLOW_VIEW = ActionMeta(
        id="platform_taskflow_view",
        name=_("全局任务查看"),
        name_en="platform_taskflow_view",
        type="manage",
        related_actions=[],
        related_resource_types=[],
        group=_("平台管理"),
        subgroup="",
        common_labels=[],
    )

    PLATFORM_HEALTHY_REPORT_VIEW = ActionMeta(
        id="platform_healthy_report_view",
        name=_("全局巡检报告查看"),
        name_en="platform_healthy_report_view",
        type="manage",
        related_actions=[],
        related_resource_types=[],
        group=_("平台管理"),
        subgroup="",
        common_labels=[],
    )

    PLATFORM_ALERT_EVENT_VIEW = ActionMeta(
        id="platform_alert_event_view",
        name=_("全局告警事件查看"),
        name_en="platform_alert_event_view",
        type="view",
        related_actions=[],
        related_resource_types=[],
        group=_("平台管理"),
        subgroup="",
        common_labels=[],
    )

    PLATFROM_RISK_MEMO_VIEW = ActionMeta(
        id="platform_risk_memo_view",
        name=_("全局风险备忘录查看"),
        name_en="platform_risk_memo_view",
        type="view",
        related_actions=[],
        related_resource_types=[],
        group=_("平台管理"),
        subgroup="",
        common_labels=[],
    )

    PLATFORM_TODO_REMIND_MANAGE = ActionMeta(
        id="platform_todo_remind_manage",
        name=_("每日待办提醒管理"),
        name_en="platform_todo_remind_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[],
        group=_("全局设置"),
        subgroup="",
        common_labels=[],
    )

    MYSQL_DBCONSOLE = ActionMeta(
        id="mysql_dbconsole",
        name=_("MySQL 管理控制台"),
        name_en="mysql_dbconsole",
        type="view",
        related_actions=[PLATFORM_MANAGE.id],
        related_resource_types=[],
        group=_("平台管理"),
        hidden=True,
    )

    TENDBCLUSTER_DBCONSOLE = ActionMeta(
        id="tendbcluster_dbconsole",
        name=_("TendbCluster 管理控制台"),
        name_en="tendbcluster_dbconsole",
        type="view",
        related_actions=[PLATFORM_MANAGE.id],
        related_resource_types=[],
        group=_("平台管理"),
        hidden=True,
    )

    SQLSERVER_DBCONSOLE = ActionMeta(
        id="sqlserver_dbconsole",
        name=_("SQLServer 管理控制台"),
        name_en="sqlserver_dbconsole",
        type="view",
        related_actions=[PLATFORM_MANAGE.id],
        related_resource_types=[],
        group=_("平台管理"),
        common_labels=[],
        hidden=True,
    )

    DBCONFIG_EDIT = ActionMeta(
        id="dbconfig_edit",
        name=_("业务参数配置编辑"),
        name_en="dbconfig_edit",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.BUSINESS, ResourceEnum.DBTYPE],
        group=_("业务"),
        subgroup=_("数据库配置"),
    )

    MYSQL_DBCONFIG_EDIT = ActionMeta(
        id="mysql_dbconfig_edit",
        name=_("MySQL 集群参数配置编辑"),
        name_en="mysql_dbconfig_edit",
        type="manage",
        related_actions=["mysql_view"],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("集群管理"),
    )

    TENDBCLUSTER_DBCONFIG_EDIT = ActionMeta(
        id="tendbcluster_dbconfig_edit",
        name=_("TenDBCluster 集群参数配置编辑"),
        name_en="tendbcluster_dbconfig_edit",
        type="manage",
        related_actions=["tendbcluster_view"],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TenDBCluster"),
        subgroup=_("集群管理"),
    )

    REDIS_DBCONFIG_EDIT = ActionMeta(
        id="redis_dbconfig_edit",
        name=_("Redis 集群参数配置编辑"),
        name_en="redis_dbconfig_edit",
        type="manage",
        related_actions=["redis_view"],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
    )

    MONGODB_DBCONFIG_EDIT = ActionMeta(
        id="mongodb_dbconfig_edit",
        name=_("MongoDB 集群参数配置编辑"),
        name_en="mongodb_dbconfig_edit",
        type="manage",
        related_actions=["mongodb_view"],
        related_resource_types=[ResourceEnum.MONGODB],
        group=_("MongoDB"),
        subgroup=_("集群管理"),
    )

    SQLSERVER_DBCONFIG_EDIT = ActionMeta(
        id="sqlserver_dbconfig_edit",
        name=_("SQLServer 集群参数配置编辑"),
        name_en="sqlserver_dbconfig_edit",
        description=_("编辑集群的参数配置"),
        type="manage",
        related_actions=["sqlserver_view"],
        related_resource_types=[ResourceEnum.SQLSERVER],
        group=_("SQLServer"),
        subgroup=_("集群管理"),
    )

    ES_DBCONFIG_EDIT = ActionMeta(
        id="es_dbconfig_edit",
        name=_("ES 集群参数配置编辑"),
        name_en="es_dbconfig_edit",
        type="manage",
        related_actions=["es_view"],
        related_resource_types=[ResourceEnum.ES],
        group=_("ElasticSearch"),
        subgroup=_("集群管理"),
    )

    KAFKA_DBCONFIG_EDIT = ActionMeta(
        id="kafka_dbconfig_edit",
        name=_("Kafka 集群参数配置编辑"),
        name_en="kafka_dbconfig_edit",
        type="manage",
        related_actions=["kafka_view"],
        related_resource_types=[ResourceEnum.KAFKA],
        group=_("Kafka"),
        subgroup=_("集群管理"),
    )

    HDFS_DBCONFIG_EDIT = ActionMeta(
        id="hdfs_dbconfig_edit",
        name=_("HDFS 集群参数配置编辑"),
        name_en="hdfs_dbconfig_edit",
        type="manage",
        related_actions=["hdfs_view"],
        related_resource_types=[ResourceEnum.HDFS],
        group=_("HDFS"),
        subgroup=_("集群管理"),
    )

    PULSAR_DBCONFIG_EDIT = ActionMeta(
        id="pulsar_dbconfig_edit",
        name=_("Pulsar 集群参数配置编辑"),
        name_en="pulsar_dbconfig_edit",
        type="manage",
        related_actions=["pulsar_view"],
        related_resource_types=[ResourceEnum.PULSAR],
        group=_("Pulsar"),
        subgroup=_("集群管理"),
    )

    DORIS_DBCONFIG_EDIT = ActionMeta(
        id="doris_dbconfig_edit",
        name=_("Doris 集群参数配置编辑"),
        name_en="doris_dbconfig_edit",
        type="manage",
        related_actions=["doris_view"],
        related_resource_types=[ResourceEnum.DORIS],
        group=_("Doris"),
        subgroup=_("集群管理"),
    )

    RIAK_DBCONFIG_EDIT = ActionMeta(
        id="riak_dbconfig_edit",
        name=_("Riak 集群参数配置编辑"),
        name_en="riak_dbconfig_edit",
        type="manage",
        related_actions=["riak_view"],
        related_resource_types=[ResourceEnum.RIAK],
        group=_("Riak"),
        subgroup=_("集群管理"),
    )

    VM_DBCONFIG_EDIT = ActionMeta(
        id="vm_dbconfig_edit",
        name=_("VM 集群参数配置编辑"),
        name_en="vm_dbconfig_edit",
        type="manage",
        related_actions=["vm_view"],
        related_resource_types=[ResourceEnum.VM],
        group=_("VM"),
        subgroup=_("集群管理"),
    )

    ORACLE_DBCONFIG_EDIT = ActionMeta(
        id="oracle_dbconfig_edit",
        name=_("Oracle 集群参数配置编辑"),
        name_en="oracle_dbconfig_edit",
        type="manage",
        related_actions=["oracle_view"],
        related_resource_types=[ResourceEnum.ORACLE],
        group=_("Oracle"),
        subgroup=_("集群管理"),
    )

    GLOBAL_DBCONFIG_EDIT = ActionMeta(
        id="global_dbconfig_edit",
        name=_("全局参数配置编辑"),
        name_en="global_dbconfig_edit",
        type="manage",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("全局设置"),
        subgroup=_("数据库配置定义"),
        hidden=True,
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
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
        common_labels=[
            CommonActionLabel.BIZ_READ_ONLY,
            CommonActionLabel.BIZ_MAINTAIN,
            CommonActionLabel.DEVELOPER,
            CommonActionLabel.EXTERNAL_DEVELOPER
        ],
    )

    MYSQL_EDIT = ActionMeta(
        id="mysql_edit",
        name=_("MySQL 集群元数据编辑"),
        name_en="MySQL Edit",
        description=_("编辑集群的标签、别名、备注、容灾要求、地域信息等元数据"),
        type="edit",
        hidden=True,
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    MYSQL_SUBSCRIBE_MONITOR = ActionMeta(
        id="mysql_subscribe_monitor",
        name=_("MySQL 集群告警订阅"),
        name_en="mysql_subscribe_monitor",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    MYSQL_IMPORT_SQLFILE = ActionMeta(
        id=TicketType.MYSQL_IMPORT_SQLFILE.lower(),
        related_resource_types=[ResourceEnum.MYSQL],
        subgroup=_("查询与变更"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.MYSQL_IMPORT_SQLFILE, CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MYSQL_DUMP_DATA = ActionMeta(
        id=TicketType.MYSQL_DUMP_DATA.lower(),
        related_resource_types=[ResourceEnum.MYSQL],
        subgroup=_("查询与变更"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.EXTERNAL_DEVELOPER, CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MYSQL_WEBCONSOLE = ActionMeta(
        id="mysql_webconsole",
        name=_("MySQL Webconsole执行"),
        name_en="mysql_webconsole",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("查询与变更"),
        common_labels=[
            CommonActionLabel.BIZ_READ_ONLY,
            CommonActionLabel.BIZ_MAINTAIN,
            CommonActionLabel.DEVELOPER,
            CommonActionLabel.EXTERNAL_DEVELOPER
        ],
    )

    MYSQL_DATA_MIGRATE = ActionMeta(
        id=TicketType.MYSQL_DATA_MIGRATE.lower(),
        subgroup=_("克隆与开区"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    MYSQL_FLASHBACK = ActionMeta(
        id=TicketType.MYSQL_FLASHBACK.lower(),
        subgroup=_("数据恢复"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MYSQL_ROLLBACK = ActionMeta(
        id=TicketType.MYSQL_ROLLBACK.lower(),
        name=_("MySQL 原地回档"),
        name_en="MYSQL_ROLLBACK",
        type="execute",
        related_actions=[],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("数据恢复"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MYSQL_ROLLBACK_CLUSTER = ActionMeta(
        id=TicketType.MYSQL_ROLLBACK_CLUSTER.lower(),
        name=_("MySQL 构造"),
        name_en="MYSQL_ROLLBACK_CLUSTER",
        type="execute",
        related_actions=[],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("数据恢复"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MYSQL_HA_DB_TABLE_BACKUP = ActionMeta(
        id=TicketType.MYSQL_HA_DB_TABLE_BACKUP.lower(),
        subgroup=_("备份"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MYSQL_HA_FULL_BACKUP = ActionMeta(
        id=TicketType.MYSQL_HA_FULL_BACKUP.lower(),
        subgroup=_("备份"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    MYSQL_LOADBALANCE_MANAGE = ActionMeta(
        id="mysql_loadbalance_manage",
        name=_("MySQL 负载均衡管理"),
        name_en="mysql_loadbalance_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MYSQL_OPENAREA_MANAGE = ActionMeta(
        id="mysql_openarea_manage",
        name=_("MySQL 开区模板管理"),
        name_en="mysql_openarea_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MySQL"),
        subgroup=_("克隆与开区"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MYSQL_PRIV_MANAGE = ActionMeta(
        id="mysql_priv_manage",
        name=_("MySQL 权限管理"),
        name_en="mysql_priv_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MySQL"),
        subgroup=_("权限管理"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MYSQL_AUTHORIZE = ActionMeta(
        id="mysql_authorize",
        name=_("MySQL 授权"),
        name_en="mysql_authorize",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("权限管理"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MYSQL_PARTITION_MANAGE = ActionMeta(
        id="mysql_partition_manage",
        name=_("MySQL 分区管理"),
        name_en="mysql_partition_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MySQL"),
        subgroup=_("分区管理"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MYSQL_TRUNCATE_DATA = ActionMeta(
        id="mysql_truncate_data",
        name=_("MySQL 清档"),
        name_en="MYSQL_TRUNCATE_DATA",
        type="execute",
        related_actions=[],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("数据清理"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MYSQL_RENAME_DATABASE = ActionMeta(
        id=TicketType.MYSQL_RENAME_DATABASE.lower(),
        subgroup=_("查询与变更"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MYSQL_HA_FULL_BACKUP = ActionMeta(
        id=TicketType.MYSQL_HA_FULL_BACKUP.lower(),
        subgroup=_("备份"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    MYSQL_OPENAREA = ActionMeta(
        id="mysql_openarea",
        name=_("MySQL开区执行"),
        name_en="mysql_openarea",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("克隆与开区"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    TENDBCLUSTER_VIEW = ActionMeta(
        id="tendbcluster_view",
        name=_("TenDB Cluster 集群详情查看"),
        name_en="tendbcluster_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TenDBCluster"),
        subgroup=_("集群管理"),
        common_labels=[
            CommonActionLabel.BIZ_READ_ONLY,
            CommonActionLabel.BIZ_MAINTAIN,
            CommonActionLabel.DEVELOPER,
            CommonActionLabel.EXTERNAL_DEVELOPER
        ],
    )

    TENDBCLUSTER_EDIT = ActionMeta(
        id="tendbcluster_edit",
        name=_("TenDB Cluster 集群元数据编辑"),
        name_en="tendbcluster_edit",
        description=_("编辑集群的标签、别名、备注、容灾要求、地域信息等元数据"),
        type="edit",
        hidden=True,
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TenDBCluster"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    TENDBCLUSTER_LOADBALANCE_MANAGE = ActionMeta(
        id="tendbcluster_loadbalance_manage",
        name=_("TenDB Cluster 负载均衡管理"),
        name_en="tendbcluster_loadbalance_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TenDBCluster"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    TENDBCLUSTER_OPENAREA_MANAGE = ActionMeta(
        id="tendbcluster_openarea_manage",
        name=_("TenDB Cluster 开区模板管理"),
        name_en="tendbcluster_openarea_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("TenDBCluster"),
        subgroup=_("克隆与开区"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    TENDBCLUSTER_PRIV_MANAGE = ActionMeta(
        id="tendbcluster_priv_manage",
        name=_("TenDB Cluster 权限管理"),
        name_en="tendbcluster_priv_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("TenDBCluster"),
        subgroup=_("权限管理"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    TENDBCLUSTER_AUTHORIZE = ActionMeta(
        id="tendbcluster_authorize",
        name=_("TenDBCluster 授权"),
        name_en="tendbcluster_authorize",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TenDBCluster"),
        subgroup=_("权限管理"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    TENDBCLUSTER_PARTITION_MANAGE = ActionMeta(
        id="tendbcluster_partition_manage",
        name=_("TenDBCluster 分区管理"),
        name_en="tendbcluster_partition_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("TenDBCluster"),
        subgroup=_("分区管理"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    TENDBCLUSTER_SUBSCRIBE_MONITOR = ActionMeta(
        id="tendbcluster_subscribe_monitor",
        name=_("TendbCluster 集群告警订阅"),
        name_en="tendbcluster_subscribe_monitor",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TenDBCluster"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    TENDBCLUSTER_IMPORT_SQLFILE = ActionMeta(
        id=TicketType.TENDBCLUSTER_IMPORT_SQLFILE.lower(),
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        subgroup=_("查询与变更"),
        is_ticket_action=True,
        common_labels=[
            CommonActionLabel.TENDBCLUSTER_IMPORT_SQLFILE,
            CommonActionLabel.DEVELOPER,
            CommonActionLabel.BIZ_MAINTAIN],
    )

    TENDBCLUSTER_DUMP_DATA = ActionMeta(
        id=TicketType.TENDBCLUSTER_DUMP_DATA.lower(),
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        subgroup=_("查询与变更"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.EXTERNAL_DEVELOPER, CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    TENDBCLUSTER_WEBCONSOLE = ActionMeta(
        id="tendbcluster_webconsole",
        name=_("TendbCluster Webconsole执行"),
        name_en="tendbcluster_webconsole",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TenDBCluster"),
        subgroup=_("查询与变更"),
        common_labels=[
            CommonActionLabel.BIZ_READ_ONLY,
            CommonActionLabel.BIZ_MAINTAIN,
            CommonActionLabel.DEVELOPER,
            CommonActionLabel.EXTERNAL_DEVELOPER
        ],
    )

    TENDBCLUSTER_OPENAREA = ActionMeta(
        id="tendbcluster_openarea",
        name=_("TenDBCluster 开区执行"),
        name_en="tendbcluster_openarea",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TenDBCluster"),
        subgroup=_("克隆与开区"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    TENDBCLUSTER_DB_TABLE_BACKUP = ActionMeta(
        id=TicketType.TENDBCLUSTER_DB_TABLE_BACKUP.lower(),
        subgroup=_("备份"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    TENDBCLUSTER_DESTROY = ActionMeta(
        id=TicketType.TENDBCLUSTER_DESTROY.lower(),
        subgroup=_("备份"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    TENDBCLUSTER_TRUNCATE_DATABASE = ActionMeta(
        id=TicketType.TENDBCLUSTER_TRUNCATE_DATABASE.lower(),
        subgroup=_("数据清理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    TENDBCLUSTER_RENAME_DATABASE = ActionMeta(
        id=TicketType.TENDBCLUSTER_RENAME_DATABASE.lower(),
        subgroup=_("查询与变更"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    TENDBCLUSTER_TEMPORARY_DESTROY = ActionMeta(
        id=TicketType.TENDBCLUSTER_TEMPORARY_DESTROY.lower(),
        subgroup=_("集群管理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    TENDBCLUSTER_FLASHBACK = ActionMeta(
        id=TicketType.TENDBCLUSTER_FLASHBACK.lower(),
        subgroup=_("数据恢复"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    TENDBCLUSTER_FULL_BACKUP = ActionMeta(
        id=TicketType.TENDBCLUSTER_FULL_BACKUP.lower(),
        subgroup=_("数据恢复"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    TENDBCLUSTER_ROLLBACK = ActionMeta(
        id=TicketType.TENDBCLUSTER_ROLLBACK.lower(),
        name=_("TenDB Cluster 原地回档"),
        name_en="TENDBCLUSTER_ROLLBACK",
        type="execute",
        related_actions=[],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TenDBCluster"),
        subgroup=_("数据恢复"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    TENDBCLUSTER_ROLLBACK_CLUSTER = ActionMeta(
        id=TicketType.TENDBCLUSTER_ROLLBACK_CLUSTER.lower(),
        name=_("TenDB Cluster 构造"),
        name_en="TENDBCLUSTER_ROLLBACK_CLUSTER",
        type="execute",
        related_actions=[],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TenDBCluster"),
        subgroup=_("数据恢复"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    TENDBCLUSTER_DATA_MIGRATE = ActionMeta(
        id=TicketType.TENDBCLUSTER_DATA_MIGRATE.lower(),
        subgroup=_("克隆与开区"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    TENDBCLUSTER_APPLY = ActionMeta(
        id=TicketType.TENDBCLUSTER_APPLY.lower(),
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        subgroup=_("集群管理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    TENDBCLUSTER_ENABLE_DISABLE = ActionMeta(
        id="tendbcluster_enable_disable",
        name=_("TenDB Cluster 集群禁用启用"),
        name_en="tendbcluster_enable_disable",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TenDBCluster"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],

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
        common_labels=[
            CommonActionLabel.BIZ_READ_ONLY,
            CommonActionLabel.BIZ_MAINTAIN,
            CommonActionLabel.DEVELOPER,
            CommonActionLabel.EXTERNAL_DEVELOPER
        ],
    )

    REDIS_EDIT = ActionMeta(
        id="redis_edit",
        name=_("Redis 集群元数据编辑"),
        name_en="redis_edit",
        description=_("编辑集群的标签、别名、备注、容灾要求、地域信息等元数据"),
        type="edit",
        hidden=True,
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    REDIS_WEBCONSOLE = ActionMeta(
        id="redis_webconsole",
        name=_("Redis Webconsole执行"),
        name_en="redis_webconsole",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("查询与变更"),
        common_labels=[
            CommonActionLabel.BIZ_READ_ONLY,
            CommonActionLabel.BIZ_MAINTAIN,
            CommonActionLabel.DEVELOPER,
            CommonActionLabel.EXTERNAL_DEVELOPER
        ],
    )

    REDIS_LOADBALANCE_MANAGE = ActionMeta(
        id="redis_loadbalance_manage",
        name=_("Redis 负载均衡管理"),
        name_en="redis_loadbalance_manage",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    REDIS_ACCESS_ENTRY_VIEW = ActionMeta(
        id="redis_access_entry_view",
        name=_("Redis 连接信息查看"),
        name_en="redis_access_entry_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    REDIS_SUBSCRIBE_MONITOR = ActionMeta(
        id="redis_subscribe_monitor",
        name=_("Redis 集群告警订阅"),
        name_en="redis_subscribe_monitor",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    REDIS_SOURCE_ACCESS_VIEW = ActionMeta(
        id="redis_source_access_view",
        name=_("Redis 访问来源查看"),
        name_en="redis_source_access_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    REDIS_CLUSTER_APPLY = ActionMeta(
        id=TicketType.REDIS_CLUSTER_APPLY.lower(),
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        subgroup=_("集群管理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    REDIS_BACKUP = ActionMeta(
        id=TicketType.REDIS_BACKUP.lower(),
        subgroup=_("备份"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    REDIS_CLUSTER_DATA_COPY = ActionMeta(
        id=TicketType.REDIS_CLUSTER_DATA_COPY.lower(),
        subgroup=_("数据复制与构造"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    REDIS_CLUSTER_ROLLBACK_DATA_COPY = ActionMeta(
        id=TicketType.REDIS_CLUSTER_ROLLBACK_DATA_COPY.lower(),
        subgroup=_("数据复制与构造"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    REDIS_DATA_STRUCTURE = ActionMeta(
        id=TicketType.REDIS_DATA_STRUCTURE.lower(),
        subgroup=_("数据复制与构造"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    REDIS_DATA_STRUCTURE_TASK_DELETE = ActionMeta(
        id=TicketType.REDIS_DATA_STRUCTURE_TASK_DELETE.lower(),
        subgroup=_("数据复制与构造"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    REDIS_DESTROY = ActionMeta(
        id=TicketType.REDIS_DESTROY.lower(),
        subgroup=_("集群管理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    REDIS_PURGE = ActionMeta(
        id=TicketType.REDIS_PURGE.lower(),
        subgroup=_("数据清理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    REDIS_KEYS_EXTRACT = ActionMeta(
        id=TicketType.REDIS_KEYS_EXTRACT.lower(),
        subgroup=_("查询与变更"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    REDIS_KEYS_DELETE = ActionMeta(
        id=TicketType.REDIS_KEYS_DELETE.lower(),
        subgroup=_("查询与变更"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    REDIS_HOT_KEY_ANALYSIS = ActionMeta(
        id=TicketType.REDIS_HOT_KEY_ANALYSIS.lower(),
        subgroup=_("查询与变更"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    REDIS_INSTANCE_DESTROY = ActionMeta(
        id=TicketType.REDIS_INSTANCE_DESTROY.lower(),
        subgroup=_("集群管理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    REDIS_KEYSTAT = ActionMeta(
        id=TicketType.REDIS_KEYSTAT.lower(),
        subgroup=_("查询与变更"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    # TODO: 暂时屏蔽对influxdb的鉴权
    # INFLUXDB_VIEW = ActionMeta(
    #     id="influxdb_view",
    #     name=_("InfluxDB 实例查看"),
    #     name_en="influxdb_view",
    #     type="view",
    #     related_actions=[DB_MANAGE.id],
    #     related_resource_types=[ResourceEnum.INFLUXDB],
    #     group=_("InfluxDB"),
    #     subgroup=_("实例管理"),
    # )
    #
    #
    # INFLUXDB_ENABLE_DISABLE = ActionMeta(
    #     id="influxdb_enable_disable",
    #     name=_("InfluxDB 实例禁用启用"),
    #     name_en="influxdb_enable_disable",
    #     type="execute",
    #     related_actions=[INFLUXDB_VIEW.id],
    #     related_resource_types=[ResourceEnum.INFLUXDB],
    #     group=_("InfluxDB"),
    #     subgroup=_("实例管理"),
    # )
    # TODO: 这里的分组管理设计不仅仅针对influxdb使用。
    #  不过目前只有influxdb使用了分组的概念，所以暂归属到InfluxDB中
    # GROUP_MANAGE = ActionMeta(
    #     id="group_manage",
    #     name=_("InfluxDB 分组管理"),
    #     name_en="group_manage",
    #     type="manage",
    #     related_actions=[DB_MANAGE.id],
    #     related_resource_types=[ResourceEnum.BUSINESS],
    #     group=_("InfluxDB"),
    #     subgroup=_("实例管理"),
    # )

    ES_APPLY = ActionMeta(
        id="es_apply",
        name=_("ES 集群部署"),
        name_en="es_apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("ElasticSearch"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    ES_VIEW = ActionMeta(
        id="es_view",
        name=_("ES 集群详情查看"),
        name_en="es_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.ES],
        group=_("ElasticSearch"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_READ_ONLY, CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    ES_EDIT = ActionMeta(
        id="es_edit",
        name=_("ES 集群元数据编辑"),
        name_en="es_edit",
        description=_("编辑集群的标签、别名、备注、容灾要求、地域信息等元数据"),
        type="edit",
        hidden=True,
        related_actions=[ES_VIEW.id],
        related_resource_types=[ResourceEnum.ES],
        group=_("ElasticSearch"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    ES_DESTROY = ActionMeta(
        id=TicketType.ES_DESTROY.lower(),
        name=_("ES 集群删除"),
        name_en="ES_DESTROY",
        type="execute",
        related_resource_types=[ResourceEnum.ES],
        group=_("ElasticSearch"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    ES_LOADBALANCE_MANAGE = ActionMeta(
        id="es_loadbalance_manage",
        name=_("ES 负载均衡管理"),
        name_en="es_loadbalance_manage",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.ES],
        group=_("ElasticSearch"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    ES_SUBSCRIBE_MONITOR = ActionMeta(
        id="es_subscribe_monitor",
        name=_("ES 集群告警订阅"),
        name_en="es_subscribe_monitor",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.ES],
        group=_("ElasticSearch"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    VM_APPLY = ActionMeta(
        id="vm_apply",
        name=_("VM 集群部署"),
        name_en="vm_apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("VM"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    VM_VIEW = ActionMeta(
        id="vm_view",
        name=_("VM 集群详情查看"),
        name_en="vm_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.VM],
        group=_("VM"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.BIZ_READ_ONLY, CommonActionLabel.DEVELOPER],
    )

    VM_EDIT = ActionMeta(
        id="vm_edit",
        name=_("VM 集群元数据编辑"),
        name_en="vm_edit",
        description=_("编辑集群的标签、别名、备注、容灾要求、地域信息等元数据"),
        type="edit",
        hidden=True,
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.VM],
        group=_("VM"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    ES_ACCESS_ENTRY_VIEW = ActionMeta(
        id="es_access_entry_view",
        name=_("ES 连接信息查看"),
        name_en="es_access_entry_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.ES],
        group=_("ElasticSearch"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    ES_ENABLE_DISABLE = ActionMeta(
        id="es_enable_disable",
        name=_("ES 集群禁用启用"),
        name_en="es_enable_disable",
        type="execute",
        related_actions=[ES_VIEW.id],
        related_resource_types=[ResourceEnum.ES],
        group=_("ElasticSearch"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    VM_ENABLE_DISABLE = ActionMeta(
        id="vm_enable_disable",
        name=_("VictoriaMetrics 集群禁用/启用"),
        name_en="vm_enable_disable",
        type="execute",
        related_actions=[VM_VIEW.id],
        related_resource_types=[ResourceEnum.VM],
        group=_("VictoriaMetrics"),
        subgroup=_("集群管理")
    )

    DORIS_APPLY = ActionMeta(
        id=TicketType.DORIS_APPLY.lower(),
        related_resource_types=[ResourceEnum.BUSINESS],
        subgroup=_("集群管理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    DORIS_VIEW = ActionMeta(
        id="doris_view",
        name=_("Doris 集群详情查看"),
        name_en="doris_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.DORIS],
        group=_("Doris"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_READ_ONLY, CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    DORIS_EDIT = ActionMeta(
        id="doris_edit",
        name=_("Doris 集群元数据编辑"),
        name_en="doris_edit",
        description=_("编辑集群的标签、别名、备注、容灾要求、地域信息等元数据"),
        type="edit",
        hidden=True,
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.DORIS],
        group=_("Doris"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    DORIS_DESTROY = ActionMeta(
        id=TicketType.DORIS_DESTROY.lower(),
        name=_("Doris 集群删除"),
        name_en="DORIS_DESTROY",
        type="execute",
        related_resource_types=[ResourceEnum.DORIS],
        group=_("Doris"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    DORIS_SUBSCRIBE_MONITOR = ActionMeta(
        id="doris_subscribe_monitor",
        name=_("Doris 集群告警订阅"),
        name_en="doris_subscribe_monitor",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.DORIS],
        group=_("Doris"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    DORIS_ACCESS_ENTRY_VIEW = ActionMeta(
        id="doris_access_entry_view",
        name=_("Doris 连接信息查看"),
        name_en="doris_access_entry_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.DORIS],
        group=_("Doris"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    DORIS_ENABLE_DISABLE = ActionMeta(
        id="doris_enable_disable",
        name=_("Doris 集群禁用启用"),
        name_en="doris_enable_disable",
        type="execute",
        related_actions=[DORIS_VIEW.id],
        related_resource_types=[ResourceEnum.DORIS],
        group=_("Doris"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_READ_ONLY, CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    KAFKA_EDIT = ActionMeta(
        id="kafka_edit",
        name=_("Kafka 集群元数据编辑"),
        name_en="kafka_edit",
        description=_("编辑集群的标签、别名、备注、容灾要求、地域信息等元数据"),
        type="edit",
        hidden=True,
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.KAFKA],
        group=_("Kafka"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    KAFKA_DESTROY = ActionMeta(
        id=TicketType.KAFKA_DESTROY.lower(),
        name=_("Kafka 集群删除"),
        name_en="KAFKA_DESTROY",
        type="execute",
        related_resource_types=[ResourceEnum.KAFKA],
        group=_("Kafka"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    KAFKA_SUBSCRIBE_MONITOR = ActionMeta(
        id="kafka_subscribe_monitor",
        name=_("Kafka 集群告警订阅"),
        name_en="kafka_subscribe_monitor",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.KAFKA],
        group=_("Kafka"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    KAFKA_ACCESS_ENTRY_VIEW = ActionMeta(
        id="kafka_access_entry_view",
        name=_("Kafka 连接信息查看"),
        name_en="kafka_access_entry_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.KAFKA],
        group=_("Kafka"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    KAFKA_APPLY = ActionMeta(
        id=TicketType.KAFKA_APPLY.lower(),
        related_resource_types=[ResourceEnum.BUSINESS],
        subgroup=_("集群管理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    HDFS_APPLY = ActionMeta(
        id=TicketType.HDFS_APPLY.lower(),
        related_resource_types=[ResourceEnum.BUSINESS],
        subgroup=_("集群管理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
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
        common_labels=[CommonActionLabel.BIZ_READ_ONLY, CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    HDFS_EDIT = ActionMeta(
        id="hdfs_edit",
        name=_("HDFS 集群元数据编辑"),
        name_en="hdfs_edit",
        description=_("编辑集群的标签、别名、备注、容灾要求、地域信息等元数据"),
        type="edit",
        hidden=True,
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.HDFS],
        group=_("HDFS"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    HDFS_DESTROY = ActionMeta(
        id=TicketType.HDFS_DESTROY.lower(),
        name=_("HDFS 集群删除"),
        name_en="HDFS_DESTROY",
        type="execute",
        related_resource_types=[ResourceEnum.HDFS],
        group=_("HDFS"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    HDFS_SUBSCRIBE_MONITOR = ActionMeta(
        id="hdfs_subscribe_monitor",
        name=_("HDFS 集群告警订阅"),
        name_en="hdfs_subscribe_monitor",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.HDFS],
        group=_("HDFS"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    HDFS_ACCESS_ENTRY_VIEW = ActionMeta(
        id="hdfs_access_entry_view",
        name=_("HDFS 连接信息查看"),
        name_en="hdfs_access_entry_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.HDFS],
        group=_("HDFS"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    PULSAR_APPLY = ActionMeta(
        id=TicketType.PULSAR_APPLY.lower(),
        related_resource_types=[ResourceEnum.BUSINESS],
        subgroup=_("集群管理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_READ_ONLY, CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    PULSAR_EDIT = ActionMeta(
        id="pulsar_edit",
        name=_("Pulsar 集群元数据编辑"),
        name_en="pulsar_edit",
        description=_("编辑集群的标签、别名、备注、容灾要求、地域信息等元数据"),
        type="edit",
        hidden=True,
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.PULSAR],
        group=_("Pulsar"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    PULSAR_DESTROY = ActionMeta(
        id=TicketType.PULSAR_DESTROY.lower(),
        subgroup=_("集群管理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    PULSAR_SUBSCRIBE_MONITOR = ActionMeta(
        id="pulsar_subscribe_monitor",
        name=_("Pulsar 集群告警订阅"),
        name_en="pulsar_subscribe_monitor",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.PULSAR],
        group=_("Pulsar"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    PULSAR_ACCESS_ENTRY_VIEW = ActionMeta(
        id="pulsar_access_entry_view",
        name=_("Pulsar 获取访问方式"),
        name_en="pulsar_access_entry_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.PULSAR],
        group=_("Pulsar"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    RIAK_CLUSTER_APPLY = ActionMeta(
        id=TicketType.RIAK_CLUSTER_APPLY.lower(),
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        subgroup=_("集群管理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    RIAK_CLUSTER_DESTROY = ActionMeta(
        id=TicketType.RIAK_CLUSTER_DESTROY.lower(),
        subgroup=_("集群管理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_READ_ONLY, CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    RIAK_EDIT = ActionMeta(
        id="riak_edit",
        name=_("Riak 集群元数据编辑"),
        name_en="riak_edit",
        description=_("编辑集群的标签、别名、备注、容灾要求、地域信息等元数据"),
        type="edit",
        hidden=True,
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.RIAK],
        group=_("Riak"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    RIAK_ACCESS_ENTRY_VIEW = ActionMeta(
        id="riak_access_entry_view",
        name=_("Riak 连接信息查看"),
        name_en="riak_access_entry_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.RIAK],
        group=_("Riak"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_READ_ONLY, CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    MONGODB_EDIT = ActionMeta(
        id="mongodb_edit",
        name=_("Mongodb 集群元数据编辑"),
        name_en="mongodb_edit",
        description=_("编辑集群的标签、别名、备注、容灾要求、地域信息等元数据"),
        type="edit",
        hidden=True,
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MONGODB],
        group=_("MongoDB"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    MONGODB_PRIV_MANAGE = ActionMeta(
        id="mongodb_priv_manage",
        name=_("MongoDB 权限管理"),
        name_en="mongodb_priv_manage",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MongoDB"),
        subgroup=_("权限管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    MONGODB_LOADBALANCE_MANAGE = ActionMeta(
        id="mongodb_loadbalance_manage",
        name=_("MongoDB 负载均衡管理"),
        name_en="mongodb_loadbalance_manage",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MONGODB],
        group=_("MongoDB"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    MONGODB_AUTHORIZE = ActionMeta(
        id="mongodb_authorize",
        name=_("MongoDB 授权"),
        name_en="mongodb_authorize",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.MONGODB],
        group=_("MongoDB"),
        subgroup=_("权限管理"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MONGODB_SUBSCRIBE_MONITOR = ActionMeta(
        id="mongodb_subscribe_monitor",
        name=_("Mongodb 集群告警订阅"),
        name_en="mongodb_subscribe_monitor",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MONGODB],
        group=_("MongoDB"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    MONGODB_SOURCE_ACCESS_VIEW = ActionMeta(
        id="mongodb_source_access_view",
        name=_("Mongodb 访问来源查看"),
        name_en="mongodb_source_access_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MONGODB],
        group=_("MongoDB"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    MONGODB_ACCESS_ENTRY_VIEW = ActionMeta(
        id="mongodb_access_entry_view",
        name=_("Mongodb 获取访问方式"),
        name_en="mongodb_access_entry_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MONGODB],
        group=_("MongoDB"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    MONGODB_WEBCONSOLE = ActionMeta(
        id="mongodb_webconsole",
        name=_("MongoDB Webconsole执行"),
        name_en="mongodb_webconsole",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MONGODB],
        group=_("MongoDB"),
        subgroup=_("查询与变更"),
        common_labels=[
            CommonActionLabel.BIZ_READ_ONLY,
            CommonActionLabel.BIZ_MAINTAIN,
            CommonActionLabel.DEVELOPER,
            CommonActionLabel.EXTERNAL_DEVELOPER
        ],
    )

    MONGODB_DATA_EXPORT = ActionMeta(
        id=TicketType.MONGODB_DATA_EXPORT.lower(),
        name=_("MongoDB 数据导出"),
        name_en="MONGODB_DATA_EXPORT",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MONGODB],
        group=_("MongoDB"),
        subgroup=_("查询与变更"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MONGODB_RESTORE = ActionMeta(
        id=TicketType.MONGODB_RESTORE.lower(),
        name=_("MongoDB 定点回档"),
        name_en="MONGODB_RESTORE",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MONGODB],
        group=_("MongoDB"),
        subgroup=_("数据恢复"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MONGODB_PITR_RESTORE = ActionMeta(
        id=TicketType.MONGODB_PITR_RESTORE.lower(),
        name=_("MongoDB Pitr回档"),
        name_en="MONGODB_PITR_RESTORE",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MONGODB],
        group=_("MongoDB"),
        subgroup=_("数据恢复"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MONGODB_REMOVE_NS = ActionMeta(
        id=TicketType.MONGODB_REMOVE_NS.lower(),
        name=_("MongoDB 清档"),
        name_en="MONGODB_REMOVE_NS",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MONGODB],
        group=_("MongoDB"),
        subgroup=_("数据清理"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MONGODB_BACKUP = ActionMeta(
        id=TicketType.MONGODB_BACKUP.lower(),
        subgroup=_("备份"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MONGODB_DESTROY = ActionMeta(
        id=TicketType.MONGODB_DESTROY.lower(),
        subgroup=_("集群管理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    MONGODB_TEMPORARY_DESTROY = ActionMeta(
        id=TicketType.MONGODB_TEMPORARY_DESTROY.lower(),
        subgroup=_("集群维护"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    MONGODB_EXEC_SCRIPT_APPLY = ActionMeta(
        id=TicketType.MONGODB_EXEC_SCRIPT_APPLY.lower(),
        name=_("MongoDB 变更脚本执行"),
        name_en="MONGODB_EXEC_SCRIPT_APPLY",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MONGODB],
        group=_("MongoDB"),
        subgroup=_("查询与变更"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    MONGODB_FULL_BACKUP = ActionMeta(
        id=TicketType.MONGODB_FULL_BACKUP.lower(),
        subgroup=_("备份"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
    )

    SQLSERVER_VIEW = ActionMeta(
        id="sqlserver_view",
        name=_("SQLServer 集群详情查看"),
        name_en="sqlserver_view",
        description=_("查看集群的基本信息、参数配置、性能监控等详情"),
        type="view",
        related_resource_types=[ResourceEnum.SQLSERVER],
        group=_("SQLServer"),
        subgroup=_("集群管理"),
        common_labels=[
            CommonActionLabel.BIZ_READ_ONLY,
            CommonActionLabel.BIZ_MAINTAIN,
            CommonActionLabel.DEVELOPER,
            CommonActionLabel.EXTERNAL_DEVELOPER,
        ],
    )

    SQLSERVER_EDIT = ActionMeta(
        id="sqlserver_edit",
        name=_("SQLServer 集群元数据编辑"),
        name_en="sqlserver_edit",
        description=_("编辑集群的标签、别名、备注等元数据"),
        type="edit",
        hidden=True,
        related_resource_types=[ResourceEnum.SQLSERVER],
        group=_("SQLServer"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    SQLSERVER_SUBSCRIBE_MONITOR = ActionMeta(
        id="sqlserver_subscribe_monitor",
        name=_("SQLServer 集群告警订阅"),
        name_en="sqlserver_subscribe_monitor",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.SQLSERVER],
        group=_("SQLServer"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    SQLSERVER_BACKUP_DBS = ActionMeta(
        id=TicketType.SQLSERVER_BACKUP_DBS.lower(),
        subgroup=_("备份"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    SQLSERVER_CLEAR_DBS = ActionMeta(
        id=TicketType.SQLSERVER_CLEAR_DBS.lower(),
        subgroup=_("数据处理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    SQLSERVER_DATA_EXPORT = ActionMeta(
        id=TicketType.SQLSERVER_DATA_EXPORT.lower(),
        subgroup=_("数据处理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    SQLSERVER_DBRENAME = ActionMeta(
        id=TicketType.SQLSERVER_DBRENAME.lower(),
        subgroup=_("集群维护"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    SQLSERVER_FULL_MIGRATE = ActionMeta(
        id=TicketType.SQLSERVER_FULL_MIGRATE.lower(),
        subgroup=_("数据处理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    SQLSERVER_IMPORT_SQLFILE = ActionMeta(
        id=TicketType.SQLSERVER_IMPORT_SQLFILE.lower(),
        subgroup=_("数据处理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    SQLSERVER_INCR_MIGRATE = ActionMeta(
        id=TicketType.SQLSERVER_INCR_MIGRATE.lower(),
        subgroup=_("数据处理"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    SQLSERVER_PRIV_MANAGE = ActionMeta(
        id="sqlserver_priv_manage",
        name=_("SQLServer 权限管理"),
        name_en="sqlserver_priv_manage",
        description=_("管理集群的账号和权限模板"),
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("SQLServer"),
        subgroup=_("权限管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    SQLSERVER_AUTHORIZE = ActionMeta(
        id="sqlserver_authorize",
        name=_("SQLServer 授权"),
        name_en="sqlserver_authorize",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.SQLSERVER],
        group=_("SQLServer"),
        subgroup=_("权限管理"),
        common_labels=[CommonActionLabel.DEVELOPER, CommonActionLabel.BIZ_MAINTAIN],
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
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    SQLSERVER_DESTROY = ActionMeta(
        id="sqlserver_destroy",
        name=_("SQLServer 集群删除"),
        name_en="SQLServer Destroy",
        type="execute",
        related_actions=[SQLSERVER_VIEW.id],
        related_resource_types=[ResourceEnum.SQLSERVER],
        group=_("SQLServer"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    ORACLE_VIEW = ActionMeta(
        id="oracle_view",
        name=_("Oracle 集群详情查看"),
        name_en="oracle_view",
        type="view",
        related_resource_types=[ResourceEnum.ORACLE],
        group=_("Oracle"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_READ_ONLY, CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    ORACLE_EDIT = ActionMeta(
        id="oracle_edit",
        name=_("Oracle 集群元数据编辑"),
        name_en="oracle_edit",
        description=_("编辑集群的标签、别名、备注、容灾要求、地域信息等元数据"),
        type="edit",
        hidden=True,
        related_resource_types=[ResourceEnum.ORACLE],
        group=_("Oracle"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    ORACLE_SUBSCRIBE_MONITOR = ActionMeta(
        id="oracle_subscribe_monitor",
        name=_("Oracle 集群告警订阅"),
        name_en="oracle_subscribe_monitor",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.ORACLE],
        group=_("Oracle"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    ORACLE_ENABLE_DISABLE = ActionMeta(
        id="oracle_enable_disable",
        name=_("Oracle 集群禁用和启用"),
        name_en="Oracle Enable Disable",
        type="execute",
        related_actions=[ORACLE_VIEW.id],
        related_resource_types=[ResourceEnum.ORACLE],
        group=_("Oracle"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    ORACLE_DESTROY = ActionMeta(
        id="oracle_destroy",
        name=_("Oracle 集群删除"),
        name_en="Oracle Destroy",
        type="execute",
        related_actions=[ORACLE_VIEW.id],
        related_resource_types=[ResourceEnum.ORACLE],
        group=_("Oracle"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    ORACLE_EXEC_SCRIPT_APPLY = ActionMeta(
        id=TicketType.ORACLE_EXEC_SCRIPT_APPLY.lower(),
        subgroup=_("脚本任务"),
        is_ticket_action=True,
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    RESOURCE_POLL_MANAGE = ActionMeta(
        id="resource_pool_manage",
        name=_("资源管理"),
        name_en="resource_pool_manage",
        type="manage",
        related_actions=[RESOURCE_MANAGE.id],
        related_resource_types=[],
        group=_("资源管理"),
        subgroup=_("资源池"),
        hidden=True,
    )

    GLOBAL_RESOURCE_TAG_MANAGE = ActionMeta(
        id="global_resource_tag_manage",
        name=_("全局标签管理"),
        name_en="global_resource_tag_manage",
        type="manage",
        related_actions=[RESOURCE_MANAGE.id],
        related_resource_types=[],
        group=_("资源管理"),
        subgroup=_("标签"),
        hidden=True,
    )

    RESOURCE_TAG_MANAGE = ActionMeta(
        id="resource_tag_manage",
        name=_("标签管理"),
        name_en="resource_tag_manage",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("业务"),
        subgroup=_("业务配置"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    NOTIFY_GROUP_MANAGE = ActionMeta(
        id="notify_group_manage",
        name=_("告警组管理"),
        name_en="notify_group_manage",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("业务"),
        subgroup=_("告警管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    MONITOR_POLICY_MANAGE = ActionMeta(
        id="monitor_policy_manage",
        name=_("告警策略管理"),
        name_en="monitor_policy_manage",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS, ResourceEnum.DBTYPE],
        group=_("业务"),
        subgroup=_("告警管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )

    GLOBAL_ALARM_POLICY_MANAGE = ActionMeta(
        id="global_alarm_policy_manage",
        name=_("全局告警策略管理"),
        name_en="global_alarm_policy_manage",
        type="manage",
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("全局设置"),
        subgroup=_("告警策略"),
    )

    ALERT_SHIELD_MANAGE = ActionMeta(
        id="alert_shield_manage",
        name=_("告警屏蔽管理"),
        name_en="alert_shield_manage",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("业务"),
        subgroup=_("告警管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    RISK_MEMO_CREATE = ActionMeta(
        id="risk_memo_create",
        name=_("风险创建"),
        name_en="risk_memo_create",
        type="create",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("业务"),
        subgroup=_("风险备忘录"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    RISK_MEMO_MANAGE = ActionMeta(
        id="risk_memo_manage",
        name=_("风险管理"),
        name_en="risk_memo_manage",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("业务"),
        subgroup=_("风险备忘录"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    DBA_ADMIN_EDIT = ActionMeta(
        id="dba_admin_edit",
        name=_("业务DBA设置"),
        name_en="dba_admin_edit",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("业务"),
        subgroup=_("业务配置"),
    )

    GLOBAL_DBA_ADMIN_EDIT = ActionMeta(
        id="global_dba_admin_edit",
        name=_("全局DBA与业务设置"),
        name_en="global_dba_admin_edit",
        type="manage",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[],
        group=_("全局设置"),
        subgroup="",
        hidden=True,
    )

    PACKAGE_VIEW = ActionMeta(
        id="package_view",
        name=_("版本文件查看"),
        name_en="package_view",
        type="view",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("全局设置"),
        subgroup=_("版本文件"),
        hidden=True,
    )

    PACKAGE_MANAGE = ActionMeta(
        id="package_manage",
        name=_("版本文件管理"),
        name_en="package_manage",
        type="manage",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("全局设置"),
        subgroup=_("版本文件"),
        hidden=True,
    )

    SET_PASSWORD_POLICY = ActionMeta(
        id="set_password_policy",
        name=_("密码安全规则设置 "),
        name_en="set_password_policy",
        type="manage",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("全局设置"),
        subgroup="",
        hidden=True,
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
        hidden=True,
    )

    SPEC_MANAGE = ActionMeta(
        id="spec_manage",
        name=_("资源规格管理"),
        name_en="spec_manage",
        type="manage",
        related_actions=[RESOURCE_MANAGE.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("资源管理"),
        subgroup=_("资源规格"),
    )

    DUTY_RULE_MANAGE = ActionMeta(
        id="duty_rule_manage",
        name=_("轮值策略管理"),
        name_en="duty_rule_manage",
        type="manage",
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("全局设置"),
        subgroup=_("轮值策略"),
    )

    IP_WHITELIST_MANAGE = ActionMeta(
        id="ip_whitelist_manage",
        name=_("授权白名单管理"),
        name_en="ip_whitelist_manage",
        type="manage",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("业务"),
        subgroup=_("业务配置"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    GLOBAL_IP_WHITELIST_MANAGE = ActionMeta(
        id="global_ip_whitelist_manage",
        name=_("全局授权白名单管理"),
        name_en="global_ip_whitelist_manage",
        type="manage",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[],
        group=_("全局设置"),
        subgroup="",
        hidden=True,
    )

    DUTY_NOTICE_CONFIG_UPDATE = ActionMeta(
        id="duty_notice_config_update",
        name=_("轮值通知设置 "),
        name_en="duty_notice_config_update",
        type="manage",
        related_actions=[GLOBAL_MANAGE.id],
        related_resource_types=[ResourceEnum.DBTYPE],
        group=_("全局设置"),
        subgroup=_("轮值策略"),
        hidden=True,
    )

    MYSQL_ADMIN_PWD_VIEW = ActionMeta(
        id="mysql_admin_pwd_view",
        name=_("MySQL 临时密码查看"),
        name_en="mysql_admin_pwd_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("集群管理"),
    )

    TENDBCLUSTER_ADMIN_PWD_VIEW = ActionMeta(
        id="tendbcluster_admin_pwd_view",
        name=_("TenDB Cluster 临时密码查看"),
        name_en="tendbcluster_admin_pwd_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TenDBCluster"),
        subgroup=_("集群管理"),
    )

    SQLSERVER_ADMIN_PWD_VIEW = ActionMeta(
        id="sqlserver_admin_pwd_view",
        name=_("SQLServer 临时密码查看"),
        name_en="sqlserver_admin_pwd_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.SQLSERVER],
        group=_("SQLServer"),
        subgroup=_("集群管理"),
    )

    # ---- MCP 工具权限 ---
    # 目前集群管理可以操作集群的工具箱单据，先给到mcp工具使用
    MYSQL_MANAGE = ActionMeta(
        id="mysql_manage",
        name=_("MySQL  集群运维管理"),
        name_en="mysql_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("集群管理"),
    )

    # MYSQL_DTS_DATA_MIGRATE / MYSQL_DTS_DATA_MIGRATE_RENAME 两个单据共用该独立权限点
    MYSQL_DTS_DATA_MIGRATE = ActionMeta(
        id="mysql_dts_data_migrate",
        name=_("MySQL DTS 数据迁移"),
        name_en="mysql_dts_data_migrate",
        type="execute",
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("数据处理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    TENDBCLUSTER_MANAGE = ActionMeta(
        id="tendbcluster_manage",
        name=_("TenDBCluster 集群运维管理"),
        name_en="tendbcluster_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TenDBCluster"),
        subgroup=_("集群管理"),
    )

    REDIS_MANAGE = ActionMeta(
        id="redis_manage",
        name=_("Redis 集群运维管理"),
        name_en="redis_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
    )

    ES_MANAGE = ActionMeta(
        id="es_manage",
        name=_("ES 集群运维管理"),
        name_en="es_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.ES],
        group=_("ElasticSearch"),
        subgroup=_("集群管理"),
    )

    DORIS_MANAGE = ActionMeta(
        id="doris_manage",
        name=_("Doris 集群运维管理"),
        name_en="doris_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.DORIS],
        group=_("Doris"),
        subgroup=_("集群管理"),
    )

    KAFKA_MANAGE = ActionMeta(
        id="kafka_manage",
        name=_("Kafka 集群运维管理"),
        name_en="kafka_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.KAFKA],
        group=_("Kafka"),
        subgroup=_("集群管理"),
    )

    HDFS_MANAGE = ActionMeta(
        id="hdfs_manage",
        name=_("HDFS 集群运维管理"),
        name_en="hdfs_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.HDFS],
        group=_("HDFS"),
        subgroup=_("集群管理"),
    )

    RIAK_MANAGE = ActionMeta(
        id="riak_manage",
        name=_("Riak 集群运维管理"),
        name_en="riak_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.RIAK],
        group=_("Riak"),
        subgroup=_("集群管理"),
    )

    PULSAR_MANAGE = ActionMeta(
        id="pulsar_manage",
        name=_("Pulsar 集群运维管理"),
        name_en="pulsar_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.PULSAR],
        group=_("Pulsar"),
        subgroup=_("集群管理"),
    )

    MONGODB_MANAGE = ActionMeta(
        id="mongodb_manage",
        name=_("MongoDB 集群运维管理"),
        name_en="mongodb_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.MONGODB],
        group=_("MongoDB"),
        subgroup=_("集群管理"),
    )

    SQLSERVER_MANAGE = ActionMeta(
        id="sqlserver_manage",
        name=_("SQLServer 集群运维管理"),
        name_en="sqlserver_manage",
        description=_("管理集群的运维操作，包括扩缩容、高可用、迁移升级、故障修复等"),
        type="manage",
        related_actions=[SQLSERVER_VIEW.id],
        related_resource_types=[ResourceEnum.SQLSERVER],
        group=_("SQLServer"),
        subgroup=_("集群管理"),
    )

    # SQLServer 原地回档：重新定义权限，不挂到常用操作 BIZ_MAINTAIN 下
    SQLSERVER_ROLLBACK_LOCAL = ActionMeta(
        id="sqlserver_rollback_local",
        name=_("SQLServer 原地回档"),
        name_en="sqlserver_rollback_local",
        description=_("SQLServer 集群原地回档操作"),
        type="execute",
        related_actions=[],
        related_resource_types=[ResourceEnum.SQLSERVER],
        group=_("SQLServer"),
        subgroup=_("数据处理"),
    )

    ORACLE_MANAGE = ActionMeta(
        id="oracle_manage",
        name=_("Oracle 集群运维管理"),
        name_en="oracle_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[ResourceEnum.ORACLE],
        group=_("Oracle"),
        subgroup=_("集群管理"),
    )

    CLOUD_MANAGE = ActionMeta(
        id="cloud_manage",
        name=_("Cloud 集群运维管理"),
        name_en="cloud_manage",
        type="manage",
        related_actions=[],
        related_resource_types=[],
        group=_("Cloud"),
        subgroup=_("集群管理"),
    )

    # --- K8s SurrealDB ---
    K8S_SURREALDB_VIEW = ActionMeta(
        id="k8s_surrealdb_view",
        name=_("K8s SurrealDB 集群详情查看"),
        name_en="k8s_surrealdb_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.K8S_SURREALDB],
        group=_("SurrealDB"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_READ_ONLY, CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )
    K8S_SURREALDB_EDIT = ActionMeta(
        id="k8s_surrealdb_edit",
        name=_("K8s SurrealDB 集群编辑"),
        name_en="k8s_surrealdb_edit",
        type="edit",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.K8S_SURREALDB],
        group=_("SurrealDB"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )
    K8S_SURREALDB_APPLY = ActionMeta(
        id="k8s_surrealdb_apply",
        name=_("K8s SurrealDB 集群部署"),
        name_en="k8s_surrealdb_apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("SurrealDB"),
        subgroup=_("集群管理"),
    )
    K8S_SURREALDB_DESTROY = ActionMeta(
        id="k8s_surrealdb_destroy",
        name=_("K8s SurrealDB 集群删除"),
        name_en="k8s_surrealdb_destroy",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.K8S_SURREALDB],
        group=_("SurrealDB"),
        subgroup=_("集群管理"),
    )
    K8S_SURREALDB_ENABLE_DISABLE = ActionMeta(
        id="k8s_surrealdb_enable_disable",
        name=_("K8S SURREALDB 集群禁用和启用"),
        name_en="K8S SURREALDB Enable Disable",
        type="execute",
        related_actions=[K8S_SURREALDB_VIEW.id],
        related_resource_types=[ResourceEnum.K8S_SURREALDB],
        group=_("SurrealDB"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )
    K8S_SURREALDB_MANAGE = ActionMeta(
        id="k8s_surrealdb_manage",
        name=_("SurrealDB 集群运维管理"),
        name_en="k8s_surrealdb_manage",
        description=_("管理集群的运维操作，包括扩缩容、高可用、迁移升级、故障修复等"),
        type="manage",
        related_actions=[K8S_SURREALDB_VIEW.id],
        related_resource_types=[ResourceEnum.K8S_SURREALDB],
        group=_("SurrealDB"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    # --- K8s Qdrant (k8s_qdrant) ---
    K8S_QDRANT_VIEW = ActionMeta(
        id="k8s_qdrant_view",
        name=_("K8s Qdrant 集群详情查看"),
        name_en="k8s_qdrant_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.K8S_QDRANT],
        group=_("QdrantDB"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_READ_ONLY, CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )
    K8S_QDRANT_EDIT = ActionMeta(
        id="k8s_qdrant_edit",
        name=_("K8s Qdrant 集群编辑"),
        name_en="k8s_qdrant_edit",
        type="edit",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.K8S_QDRANT],
        group=_("QdrantDB"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN, CommonActionLabel.DEVELOPER],
    )
    K8S_QDRANT_APPLY = ActionMeta(
        id="k8s_qdrant_apply",
        name=_("K8s Qdrant 集群部署"),
        name_en="k8s_qdrant_apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("QdrantDB"),
        subgroup=_("集群管理"),
    )

    K8S_QDRANT_DESTROY = ActionMeta(
        id="k8s_qdrant_destroy",
        name=_("K8s Qdrant 集群销毁"),
        name_en="k8s_qdrant_destroy",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.K8S_QDRANT],
        group=_("QdrantDB"),
        subgroup=_("集群管理"),
    )
    K8S_QDRANT_ENABLE_DISABLE = ActionMeta(
        id="k8s_qdrant_enable_disable",
        name=_("K8s Qdrant 集群启用/禁用"),
        name_en="k8s_qdrant_enable_disable",
        type="execute",
        related_actions=[K8S_QDRANT_VIEW.id],
        related_resource_types=[ResourceEnum.K8S_QDRANT],
        group=_("QdrantDB"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    K8S_QDRANT_MANAGE = ActionMeta(
        id="k8s_qdrant_manage",
        name=_("K8s Qdrant 集群运维管理"),
        name_en="k8s_qdrant_manage",
        type="manage",
        related_actions=[K8S_QDRANT_VIEW.id],
        related_resource_types=[ResourceEnum.K8S_QDRANT],
        group=_("QdrantDB"),
        subgroup=_("集群管理"),
        common_labels=[CommonActionLabel.BIZ_MAINTAIN],
    )

    # --- K8s VictoriaMetrics (k8s_victoriametrics) ---
    K8S_VICTORIAMETRICS_VIEW = ActionMeta(
        id="k8s_vm_view",
        name=_("K8s VictoriaMetrics 集群详情查看"),
        name_en="k8s_victoriametrics_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.K8S_VICTORIAMETRICS],
        group=_("已废弃"),
    )
    K8S_VICTORIAMETRICS_EDIT = ActionMeta(
        id="k8s_vm_edit",
        name=_("K8s VictoriaMetrics 集群编辑"),
        name_en="k8s_victoriametrics_edit",
        type="edit",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.K8S_VICTORIAMETRICS],
        group=_("已废弃"),
    )
    K8S_VICTORIAMETRICS_APPLY = ActionMeta(
        id="k8s_vm_apply",
        name=_("K8s VictoriaMetrics 集群部署"),
        name_en="k8s_victoriametrics_apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("已废弃"),
    )
    K8S_VICTORIAMETRICS_DESTROY = ActionMeta(
        id="k8s_vm_destroy",
        name=_("K8s VictoriaMetrics 集群删除"),
        name_en="k8s_victoriametrics_destroy",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.K8S_VICTORIAMETRICS],
        group=_("已废弃"),
    )
    K8S_VICTORIAMETRICS_ENABLE_DISABLE = ActionMeta(
        id="k8s_vm_enable_disable",
        name=_("K8s VictoriaMetrics 集群禁用和启用"),
        name_en="k8s_vm_enable_disable",
        type="execute",
        related_actions=[K8S_VICTORIAMETRICS_VIEW.id],
        related_resource_types=[ResourceEnum.K8S_VICTORIAMETRICS],
        group=_("已废弃"),
    )
    K8S_VICTORIAMETRICS_MANAGE = ActionMeta(
        id="k8s_vm_manage",
        name=_("VictoriaMetrics 集群运维管理"),
        name_en="k8s_victoriametrics_manage",
        description=_("管理集群的运维操作，包括扩缩容、高可用、迁移升级、故障修复等"),
        type="manage",
        related_actions=[K8S_VICTORIAMETRICS_VIEW.id],
        related_resource_types=[ResourceEnum.K8S_VICTORIAMETRICS],
        group=_("已废弃"),
    )

    # --- K8s Risingwave (k8s_risingwave) ---
    K8S_RISINGWAVE_VIEW = ActionMeta(
        id="k8s_risingwave_view",
        name=_("K8s Risingwave 集群详情查看"),
        name_en="k8s_risingwave_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.K8S_RISINGWAVE],
        group=_("已废弃"),
    )
    K8S_RISINGWAVE_EDIT = ActionMeta(
        id="k8s_risingwave_edit",
        name=_("K8s Risingwave 集群编辑"),
        name_en="k8s_risingwave_edit",
        type="edit",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.K8S_RISINGWAVE],
        group=_("已废弃"),
    )
    K8S_RISINGWAVE_APPLY = ActionMeta(
        id="k8s_risingwave_apply",
        name=_("K8s Risingwave 集群部署"),
        name_en="k8s_risingwave_apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("已废弃"),
    )
    K8S_RISINGWAVE_DESTROY = ActionMeta(
        id="k8s_risingwave_destroy",
        name=_("K8s Risingwave 集群删除"),
        name_en="k8s_risingwave_destroy",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.K8S_RISINGWAVE],
        group=_("已废弃"),
    )
    K8S_RISINGWAVE_ENABLE_DISABLE = ActionMeta(
        id="k8s_risingwave_enable_disable",
        name=_("K8S RISINGWAVE 集群禁用和启用"),
        name_en="K8S RISINGWAVE Enable Disable",
        type="execute",
        related_actions=[K8S_RISINGWAVE_VIEW.id],
        related_resource_types=[ResourceEnum.K8S_RISINGWAVE],
        group=_("已废弃"),
    )
    K8S_RISINGWAVE_MANAGE = ActionMeta(
        id="k8s_risingwave_manage",
        name=_("Risingwave 集群运维管理"),
        name_en="k8s_risingwave_manage",
        description=_("管理集群的运维操作，包括扩缩容、高可用、迁移升级、故障修复等"),
        type="manage",
        related_actions=[K8S_RISINGWAVE_VIEW.id],
        related_resource_types=[ResourceEnum.K8S_RISINGWAVE],
        group=_("已废弃"),
    )

    # --- K8s Milvus (k8s_milvus) ---
    K8S_MILVUS_VIEW = ActionMeta(
        id="k8s_milvus_view",
        name=_("K8s Milvus 集群详情查看"),
        name_en="k8s_milvus_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.K8S_MILVUS],
        group=_("已废弃"),
    )
    K8S_MILVUS_EDIT = ActionMeta(
        id="k8s_milvus_edit",
        name=_("K8s Milvus 集群编辑"),
        name_en="k8s_milvus_edit",
        type="edit",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.K8S_MILVUS],
        group=_("已废弃"),
    )
    K8S_MILVUS_APPLY = ActionMeta(
        id="k8s_milvus_apply",
        name=_("K8s Milvus 集群部署"),
        name_en="k8s_milvus_apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("已废弃"),
    )
    K8S_MILVUS_DESTROY = ActionMeta(
        id="k8s_milvus_destroy",
        name=_("K8s Milvus 集群删除"),
        name_en="k8s_milvus_destroy",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.K8S_MILVUS],
        group=_("已废弃"),
    )
    K8S_MILVUS_ENABLE_DISABLE = ActionMeta(
        id="k8s_milvus_enable_disable",
        name=_("K8S MILVUS 集群禁用和启用"),
        name_en="K8S MILVUS Enable Disable",
        type="execute",
        related_actions=[K8S_MILVUS_VIEW.id],
        related_resource_types=[ResourceEnum.K8S_MILVUS],
        group=_("已废弃"),
    )
    K8S_MILVUS_MANAGE = ActionMeta(
        id="k8s_milvus_manage",
        name=_("Milvus 集群运维管理"),
        name_en="k8s_milvus_manage",
        description=_("管理集群的运维操作，包括扩缩容、高可用、迁移升级、故障修复等"),
        type="manage",
        related_actions=[K8S_MILVUS_VIEW.id],
        related_resource_types=[ResourceEnum.K8S_MILVUS],
        group=_("已废弃"),
    )

    # --- K8s GreptimeDB (k8s_greptimedb) ---
    K8S_GREPTIMEDB_VIEW = ActionMeta(
        id="k8s_greptimedb_view",
        name=_("K8s GreptimeDB 集群详情查看"),
        name_en="k8s_greptimedb_view",
        type="view",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.K8S_GREPTIMEDB],
        group=_("已废弃"),
    )
    K8S_GREPTIMEDB_EDIT = ActionMeta(
        id="k8s_greptimedb_edit",
        name=_("K8s GreptimeDB 集群编辑"),
        name_en="k8s_greptimedb_edit",
        type="edit",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.K8S_GREPTIMEDB],
        group=_("已废弃"),
    )
    K8S_GREPTIMEDB_APPLY = ActionMeta(
        id="k8s_greptimedb_apply",
        name=_("K8s GreptimeDB 集群部署"),
        name_en="k8s_greptimedb_apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("已废弃"),
    )
    K8S_GREPTIMEDB_DESTROY = ActionMeta(
        id="k8s_greptimedb_destroy",
        name=_("K8s GreptimeDB 集群删除"),
        name_en="k8s_greptimedb_destroy",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.K8S_GREPTIMEDB],
        group=_("已废弃"),
    )
    K8S_GREPTIMEDB_ENABLE_DISABLE = ActionMeta(
        id="k8s_greptimedb_enable_disable",
        name=_("K8S GREPTIMEDB 集群禁用和启用"),
        name_en="K8S GREPTIMEDB Enable Disable",
        type="execute",
        related_actions=[K8S_GREPTIMEDB_VIEW.id],
        related_resource_types=[ResourceEnum.K8S_GREPTIMEDB],
        group=_("已废弃"),
    )
    K8S_GREPTIMEDB_MANAGE = ActionMeta(
        id="k8s_greptimedb_manage",
        name=_("GreptimeDB 集群运维管理"),
        name_en="k8s_greptimedb_manage",
        description=_("管理集群的运维操作，包括扩缩容、高可用、迁移升级、故障修复等"),
        type="manage",
        related_actions=[K8S_GREPTIMEDB_VIEW.id],
        related_resource_types=[ResourceEnum.K8S_GREPTIMEDB],
        group=_("已废弃"),
    )

    # --- K8s Addon 管理（跨存储类型，作用于 K8s 集群级别）---
    K8S_ADDON_MANAGE = ActionMeta(
        id="k8s_addon_manage",
        name=_("K8s Addon 管理"),
        name_en="k8s_addon_manage",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("已废弃"),
    )

    @classmethod
    def get_action_by_id(cls, action_id: Union[(ActionMeta, str)]) -> ActionMeta:
        if isinstance(action_id, ActionMeta):
            return action_id
        if action_id.lower() not in _all_actions:
            raise ActionNotExistError(_("动作ID不存在: {}").format(action_id))
        return _all_actions[action_id.lower()]

    @classmethod
    def get_action_by_ticket_type(cls, ticket_type: str) -> ActionMeta:
        return getattr(cls, str(ticket_type).upper())

    @classmethod
    def cluster_type_to_action(cls, cluster_type, action_key):
        """集群类型与集群详情操作的映射"""
        db_type = ClusterType.cluster_type_to_db_type(cluster_type)
        return getattr(cls, f"{db_type}_{action_key}".upper())

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
            if isinstance(action, ActionMeta) and name.lower() in action.id and action not in exclude
        ]
        return actions


# fmt: on
def register_ticket_iam_actions():
    """将单据动作注册到IAM动作类中"""
    for ticket_type in TicketType.get_values():
        ticket_enum = TicketType.__field_members__[ticket_type]
        # 如果单据类型要求不注册iam，则忽略
        if not isinstance(ticket_enum, TicketEnumField) or not ticket_enum.register_iam:
            continue
        # 优先以定义为准，否则自动注册
        if not getattr(ActionEnum, ticket_type.upper(), None):
            ticket_action = ActionMeta(id=ticket_type.lower(), subgroup=ticket_enum.subgroup, is_ticket_action=True)
            setattr(ActionEnum, ticket_type.upper(), ticket_action)


register_ticket_iam_actions()

_all_actions = {action.id: action for action in ActionEnum.__dict__.values() if isinstance(action, ActionMeta)}
