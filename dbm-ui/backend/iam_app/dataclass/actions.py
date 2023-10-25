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

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.exceptions import ActionNotExistError


@dataclass
class ActionMeta(Action):
    """action 属性定义"""

    id: str  # 动作ID
    name: str  # 动作名称
    name_en: str  # 动作英文名称
    type: str  # 动作类型
    related_resource_types: List[ResourceMeta] = None  # 关联资源类型
    related_actions: List = None  # 关联动作
    version: str = "1"  # 版本
    group: str = ""  # 动作隶属组
    subgroup: str = ""  # 动作隶属子组

    def __post_init__(self):
        super(ActionMeta, self).__init__(id=self.id)

    def to_json(self):
        content = asdict(self)
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

    MYSQL_AUTHORIZE_RULES = ActionMeta(
        id="mysql_authorize",
        name=_("MySQL 授权"),
        name_en="MySQL Authorize",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("权限管理"),
    )

    MYSQL_EXCEL_AUTHORIZE_RULES = ActionMeta(
        id="mysql_excel_authorize",
        name=_("MySQL 导入授权"),
        name_en="MySQL Excel Authorize",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MySQL"),
        subgroup=_("权限管理"),
    )

    MYSQL_IMPORT_SQLFILE = ActionMeta(
        id="mysql_import_sqlfile",
        name=_("MySQL 变更SQL执行"),
        name_en="mysql_import_sqlfile",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("SQL 任务"),
    )

    MYSQL_HA_RENAME_DATABASE = ActionMeta(
        id="mysql_ha_rename_database",
        name=_("MySQL DB重命名"),
        name_en="mysql_ha_rename_database",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("SQL 任务"),
    )

    MYSQL_CLIENT_CLONE_RULES = ActionMeta(
        id="mysql_client_clone_rules",
        name=_("MySQL 客户端权限克隆"),
        name_en="MySQL Client Clone Rules",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("MySQL"),
        subgroup=_("权限克隆"),
    )

    MYSQL_INSTANCE_CLONE_RULES = ActionMeta(
        id="mysql_instance_clone_rules",
        name=_("MySQL DB实例权限克隆"),
        name_en="MySQL Instance Clone Rules",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("权限克隆"),
    )

    MYSQL_RESTORE_LOCAL_SLAVE = ActionMeta(
        id="mysql_restore_local_slave",
        name=_("MySQL 原地重建"),
        name_en="MySQL Restore local slave",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("集群维护"),
    )

    MYSQL_RESTORE_SLAVE = ActionMeta(
        id="mysql_restore_slave",
        name=_("MySQL 新机从建"),
        name_en="mysql_restore_slave",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("集群维护"),
    )

    MYSQL_ADD_SLAVE = ActionMeta(
        id="mysql_add_slave",
        name=_("MySQL 添加从库"),
        name_en="mysql_add_slave",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("集群维护"),
    )

    MYSQL_MIGRATE_CLUSTER = ActionMeta(
        id="mysql_migrate_cluster",
        name=_("MySQL 克隆主从"),
        name_en="mysql_migrate_cluster",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("集群维护"),
    )

    MYSQL_MASTER_SLAVE_SWITCH = ActionMeta(
        id="mysql_master_slave_switch",
        name=_("MySQL 主从互切"),
        name_en="mysql_master_slave_switch",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("集群维护"),
    )

    MYSQL_PROXY_SWITCH = ActionMeta(
        id="mysql_proxy_switch",
        name=_("MySQL 替换proxy"),
        name_en="master_proxy_switch",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("集群维护"),
    )

    MYSQL_PROXY_ADD = ActionMeta(
        id="mysql_proxy_add",
        name=_("MySQL 添加proxy"),
        name_en="master_proxy_add",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("集群维护"),
    )

    MYSQL_MASTER_FAIL_OVER = ActionMeta(
        id="mysql_master_fail_over",
        name=_("MySQL 主故障切换"),
        name_en="master_master_fail_over",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("集群维护"),
    )

    MYSQL_HA_FULL_BACKUP = ActionMeta(
        id="mysql_ha_full_backup",
        name=_("MySQL 全库备份"),
        name_en="mysql_ha_full_backup",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("备份"),
    )

    MYSQL_HA_DB_TABLE_BACKUP = ActionMeta(
        id="mysql_ha_db_table_backup",
        name=_("MySQL 库表备份"),
        name_en="mysql_ha_db_table_backup",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("备份"),
    )

    MYSQL_HA_TRUNCATE_DATA = ActionMeta(
        id="mysql_ha_truncate_date",
        name=_("MySQL 清档"),
        name_en="mysql_ha_truncate_date",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("数据处理"),
    )

    MYSQL_CHECKSUM = ActionMeta(
        id="mysql_checksum",
        name=_("MySQL 数据校验修复"),
        name_en="mysql_checksum",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("数据处理"),
    )

    MYSQL_FLASHBACK = ActionMeta(
        id="mysql_flashback",
        name=_("MySQL 闪回"),
        name_en="mysql_flashback",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("回档"),
    )

    MYSQL_ROLLBACK_CLUSTER = ActionMeta(
        id="mysql_rollback_cluster",
        name=_("MySQL 定点回档"),
        name_en="mysql_rollback_cluster",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("回档"),
    )

    MYSQL_PARTITION = ActionMeta(
        id="mysql_partition",
        name=_("MySQL 分区策略执行"),
        name_en="mysql_partition",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("分区管理"),
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

    MYSQL_OPENAREA = ActionMeta(
        id="mysql_open_area",
        name=_("MySQL 开区"),
        name_en="mysql_open_area",
        type="execute",
        related_actions=[MYSQL_VIEW.id],
        related_resource_types=[ResourceEnum.MYSQL],
        group=_("MySQL"),
        subgroup=_("克隆开区"),
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

    TENDBCLUSTER_CHECKSUM = ActionMeta(
        id="tendbcluster_checksum",
        name=_("TendbCluster 数据校验修复"),
        name_en="tendbcluster_checksum",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("数据处理"),
    )

    TENDBCLUSTER_OPENAREA = ActionMeta(
        id="tendbcluster_open_area",
        name=_("TendbCluster 开区"),
        name_en="tendbcluster_open_area",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("克隆开区"),
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

    TENDBCLUSTER_PARTITION = ActionMeta(
        id="tendbcluster_partition",
        name=_("TendbCluster 分区管理"),
        name_en="tendbcluster_partition",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("分区管理"),
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

    TENDBCLUSTER_DB_TABLE_BACKUP = ActionMeta(
        id="tendbcluster_db_table_backup",
        name=_("TendbCluster 库表备份"),
        name_en="tendbcluster_db_table_backup",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("备份"),
    )

    TENDBCLUSTER_RENAME_DATABASE = ActionMeta(
        id="tendbcluster_rename_database",
        name=_("TendbCluster DB重命名"),
        name_en="tendbcluster_rename_database",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("SQL 任务"),
    )

    TENDBCLUSTER_TRUNCATE_DATABASE = ActionMeta(
        id="tendbcluster_truncate_database",
        name=_("TendbCluster 清档"),
        name_en="tendbcluster_truncate_database",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("数据处理"),
    )

    TENDBCLUSTER_MASTER_FAIL_OVER = ActionMeta(
        id="tendbcluster_master_fail_over",
        name=_("TendbCluster 主故障切换"),
        name_en="tendbcluster_master_fail_over",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("集群维护"),
    )

    TENDBCLUSTER_MASTER_SLAVE_SWITCH = ActionMeta(
        id="tendbcluster_master_slave_switch",
        name=_("TendbCluster 主从互切"),
        name_en="tendbcluster_master_slave_switch",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("集群维护"),
    )

    TENDBCLUSTER_IMPORT_SQLFILE = ActionMeta(
        id="tendbcluster_import_sqlfile",
        name=_("TendbCluster 变更SQL执行"),
        name_en="tendbcluster_import_sqlfile",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("SQL 任务"),
    )

    TENDBCLUSTER_SPIDER_ADD_NODES = ActionMeta(
        id="tendbcluster_spider_add_nodes",
        name=_("TendbCluster 扩容接入层"),
        name_en="tendbcluster_spider_add_nodes",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("集群维护"),
    )

    TENDBCLUSTER_SPIDER_REDUCE_NODES = ActionMeta(
        id="tendbcluster_spider_reduce_nodes",
        name=_("TendbCluster 缩容接入层"),
        name_en="tendbcluster_spider_reduce_nodes",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("集群维护"),
    )

    TENDBCLUSTER_SPIDER_MNT_APPLY = ActionMeta(
        id="tendbcluster_spider_mnt_apply",
        name=_("TendbCluster 添加运维节点"),
        name_en="tendbcluster_spider_mnt_apply",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("运维 Spider 管理"),
    )

    TENDBCLUSTER_SPIDER_MNT_DESTROY = ActionMeta(
        id="tendbcluster_spider_mnt_destroy",
        name=_("TendbCluster 下架运维节点"),
        name_en="tendbcluster_spider_mnt_destroy",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("运维 Spider 管理"),
    )

    TENDBCLUSTER_SPIDER_SLAVE_APPLY = ActionMeta(
        id="tendbcluster_spider_slave_apply",
        name=_("TendbCluster 部署只读接入层"),
        name_en="tendbcluster_spider_slave_apply",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("访问入口"),
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

    TENDBCLUSTER_APPLY = ActionMeta(
        id="tendbcluster_apply",
        name=_("TendbCluster 集群部署"),
        name_en="tendbcluster_apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("TendbCluster"),
        subgroup=_("集群管理"),
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

    TENDBCLUSTER_DESTROY = ActionMeta(
        id="tendbcluster_destroy",
        name=_("TendbCluster 集群删除"),
        name_en="tendbcluster_destroy",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("集群管理"),
    )

    TENDBCLUSTER_TEMPORARY_DESTROY = ActionMeta(
        id="tendbcluster_temporary_destroy",
        name=_("TendbCluster 临时集群删除"),
        name_en="tendbcluster_temporary_destroy",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("集群管理"),
    )

    TENDBCLUSTER_NODE_REBALANCE = ActionMeta(
        id="tendbcluster_node_rebalance",
        name=_("TendbCluster 集群容量变更"),
        name_en="tendbcluster_node_rebalance",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("集群维护"),
    )

    TENDBCLUSTER_FULL_BACKUP = ActionMeta(
        id="tendbcluster_full_backup",
        name=_("TendbCluster 全库备份"),
        name_en="tendbcluster_full_backup",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("备份"),
    )

    TENDBCLUSTER_ROLLBACK_CLUSTER = ActionMeta(
        id="tendbcluster_rollback_cluster",
        name=_("TendbCluster 定点构造"),
        name_en="tendbcluster_rollback_cluster",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("回档"),
    )

    TENDBCLUSTER_FLASHBACK = ActionMeta(
        id="tendbcluster_flashback",
        name=_("TendbCluster 闪回"),
        name_en="tendbcluster_flashback",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("回档"),
    )

    TENDBCLUSTER_CLIENT_CLONE_RULES = ActionMeta(
        id="tendbcluster_cluster_clone_rules",
        name=_("TendbCluster 客户端权限克隆"),
        name_en="tendbcluster_cluster_clone_rules",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("TendbCluster"),
        subgroup=_("权限克隆"),
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

    TENDBCLUSTER_AUTHORIZE_RULES = ActionMeta(
        id="tendbcluster_authorize_rules",
        name=_("TendbCluster 授权"),
        name_en="tendbcluster_authorize_rules",
        type="execute",
        related_actions=[TENDBCLUSTER_VIEW.id],
        related_resource_types=[ResourceEnum.TENDBCLUSTER],
        group=_("TendbCluster"),
        subgroup=_("权限管理"),
    )

    TENDBCLUSTER_EXCEL_AUTHORIZE_RULES = ActionMeta(
        id="tendb_excel_authorize_rules",
        name=_("TendbCluster 导入授权"),
        name_en="tendb_excel_authorize_rules",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("TendbCluster"),
        subgroup=_("权限管理"),
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

    REDIS_CLUSTER_APPLY = ActionMeta(
        id="redis_cluster_apply",
        name=_("Redis 集群部署"),
        name_en="redis_cluster_apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
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

    REDIS_DESTROY = ActionMeta(
        id="redis_destroy",
        name=_("Redis 集群删除"),
        name_en="redis_destroy",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
    )

    REDIS_KEYS_EXTRACT = ActionMeta(
        id="redis_keys_extract",
        name=_("Redis 提取 Key"),
        name_en="redis_keys_extract",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
    )

    REDIS_KEYS_DELETE = ActionMeta(
        id="redis_keys_delete",
        name=_("Redis 删除 key"),
        name_en="redis_keys_delete",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
    )

    REDIS_BACKUP = ActionMeta(
        id="redis_backup",
        name=_("Redis 集群备份"),
        name_en="redis_backup",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
    )

    REDIS_PURGE = ActionMeta(
        id="redis_purge",
        name=_("Redis 集群清档"),
        name_en="redis_purge",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
    )

    REDIS_PLUGIN_CREATE_CLB = ActionMeta(
        id="redis_plugin_create_clb",
        name=_("Redis 创建CLB"),
        name_en="redis_plugin_create_clb",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
    )

    REDIS_PLUGIN_DELETE_CLB = ActionMeta(
        id="redis_plugin_delete_clb",
        name=_("Redis 删除CLB"),
        name_en="redis_plugin_delete_clb",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
    )

    REDIS_PLUGIN_DNS_BIND_CLB = ActionMeta(
        id="redis_plugin_dns_bind_clb",
        name=_("Redis 域名绑定CLB"),
        name_en="redis_plugin_dns_bind_clb",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
    )

    REDIS_PLUGIN_DNS_UNBIND_CLB = ActionMeta(
        id="redis_plugin_dns_unbind_clb",
        name=_("Redis 域名解绑CLB"),
        name_en="redis_plugin_dns_unbind_clb",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
    )

    REDIS_PLUGIN_CREATE_POLARIS = ActionMeta(
        id="redis_plugin_create_polaris",
        name=_("Redis 创建Polaris"),
        name_en="redis_plugin_create_polaris",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
    )

    REDIS_PLUGIN_DELETE_POLARIS = ActionMeta(
        id="redis_plugin_delete_polaris",
        name=_("Redis 删除Polaris"),
        name_en="redis_plugin_delete_polaris",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群管理"),
    )

    REDIS_CLUSTER_AUTOFIX = ActionMeta(
        id="redis_cluster_autofix",
        name=_("Redis 故障自愈"),
        name_en="redis_cluster_autofix",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群维护"),
    )

    REDIS_CLUSTER_INSTANCE_SHUTDOWN = ActionMeta(
        id="redis_cluster_instance_shutdown",
        name=_("Redis 故障自愈-实例下架"),
        name_en="redis_cluster_instance_shutdown",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群维护"),
    )

    REDIS_SCALE_UPDOWN = ActionMeta(
        id="redis_scale_updown",
        name=_("Redis 集群容量变更"),
        name_en="redis_scale_updown",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群维护"),
    )

    REDIS_PROXY_SCALE_UP = ActionMeta(
        id="redis_proxy_scale_up",
        name=_("Redis 扩容接入层"),
        name_en="redis_proxy_scale_up",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群维护"),
    )

    REDIS_PROXY_SCALE_DOWN = ActionMeta(
        id="redis_proxy_scale_down",
        name=_("Redis 缩容接入层"),
        name_en="redis_proxy_scale_down",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群维护"),
    )

    REDIS_CLUSTER_SHARD_NUM_UPDATE = ActionMeta(
        id="redis_cluster_shard_num_update",
        name=_("Redis 集群分片数变更"),
        name_en="redis_cluster_shard_num_update",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群维护"),
    )

    REDIS_CLUSTER_TYPE_UPDATE = ActionMeta(
        id="redis_cluster_type_update",
        name=_("Redis 集群类型变更"),
        name_en="redis_cluster_type_update",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群维护"),
    )

    REDIS_MASTER_SLAVE_SWITCH = ActionMeta(
        id="redis_master_slave_switch",
        name=_("Redis 主从切换"),
        name_en="redis_master_slave_switch",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群维护"),
    )

    REDIS_CLUSTER_ADD_SLAVE = ActionMeta(
        id="redis_cluster_add_slave",
        name=_("Redis 重建从库"),
        name_en="redis_cluster_add_slave",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群维护"),
    )

    REDIS_CLUSTER_CUTOFF = ActionMeta(
        id="redis_cluster_cutoff",
        name=_("Redis 整机替换"),
        name_en="redis_cluster_cutoff",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("集群维护"),
    )

    REDIS_DATA_STRUCTURE = ActionMeta(
        id="redis_data_structure",
        name=_("Redis 定点构造"),
        name_en="redis_data_structure",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("数据构造"),
    )

    REDIS_DATA_STRUCTURE_MANAGE = ActionMeta(
        id="redis_data_structure_manage",
        name=_("Redis 数据构造记录管理"),
        name_en="redis_data_structure_manage",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("Redis"),
        subgroup=_("数据构造"),
    )

    REDIS_CLUSTER_ROLLBACK_DATA_COPY = ActionMeta(
        id="redis_cluster_rollback_data_copy",
        name=_("Redis 以构造实例恢复"),
        name_en="redis_cluster_rollback_data_copy",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("数据构造"),
    )

    REDIS_CLUSTER_DATA_COPY = ActionMeta(
        id="redis_cluster_data_copy",
        name=_("Redis 数据复制"),
        name_en="redis_cluster_data_copy",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.REDIS],
        group=_("Redis"),
        subgroup=_("数据传输"),
    )

    INFLUXDB_APPLY = ActionMeta(
        id="influxdb_apply",
        name=_("InfluxDB 实例部署"),
        name_en="influxdb_apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("InfluxDB"),
        subgroup=_("实例管理"),
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

    INFLUXDB_REBOOT = ActionMeta(
        id="influxdb_reboot",
        name=_("InfluxDB 实例重启"),
        name_en="influxdb_reboot",
        type="execute",
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
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.INFLUXDB],
        group=_("InfluxDB"),
        subgroup=_("实例管理"),
    )

    INFLUXDB_DESTROY = ActionMeta(
        id="influxdb_destroy",
        name=_("InfluxDB 实例删除"),
        name_en="influxdb_destroy",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.INFLUXDB],
        group=_("InfluxDB"),
        subgroup=_("实例管理"),
    )

    INFLUXDB_REPLACE = ActionMeta(
        id="influxdb_replace",
        name=_("InfluxDB 实例替换"),
        name_en="influxdb_replace",
        type="execute",
        related_actions=[DB_MANAGE.id],
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

    ES_SCALE_UP = ActionMeta(
        id="es_scale_up",
        name=_("ES 集群扩容"),
        name_en="es_scale_up",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.ES],
        group=_("ES"),
        subgroup=_("集群管理"),
    )

    ES_SHRINK = ActionMeta(
        id="es_shrink",
        name=_("ES 集群缩容"),
        name_en="es_shrink",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.ES],
        group=_("ES"),
        subgroup=_("集群管理"),
    )

    ES_REBOOT = ActionMeta(
        id="es_reboot",
        name=_("ES 集群节点重启"),
        name_en="es_reboot",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.ES],
        group=_("ES"),
        subgroup=_("集群管理"),
    )

    ES_REPLACE = ActionMeta(
        id="es_replace",
        name=_("ES 集群实例替换"),
        name_en="es_replace",
        type="execute",
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
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.ES],
        group=_("ES"),
        subgroup=_("集群管理"),
    )

    ES_DESTROY = ActionMeta(
        id="es_destroy",
        name=_("ES 集群删除"),
        name_en="es_destroy",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.ES],
        group=_("ES"),
        subgroup=_("集群管理"),
    )

    KAFKA_APPLY = ActionMeta(
        id="kafka_apply",
        name=_("Kafka 集群部署"),
        name_en="kafka_apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("Kafka"),
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

    KAFKA_SCALE_UP = ActionMeta(
        id="kafka_scale_up",
        name=_("Kafka 集群扩容"),
        name_en="kafka_scale_up",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.KAFKA],
        group=_("Kafka"),
        subgroup=_("集群管理"),
    )

    KAFKA_SHRINK = ActionMeta(
        id="kafka_shrink",
        name=_("Kafka 集群缩容"),
        name_en="kafka_shrink",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.KAFKA],
        group=_("Kafka"),
        subgroup=_("集群管理"),
    )

    KAFKA_REBOOT = ActionMeta(
        id="kafka_reboot",
        name=_("Kafka 集群节点重启"),
        name_en="kafka_reboot",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.KAFKA],
        group=_("Kafka"),
        subgroup=_("集群管理"),
    )

    KAFKA_REPLACE = ActionMeta(
        id="kafka_replace",
        name=_("Kafka 集群实例替换"),
        name_en="kafka_replace",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.KAFKA],
        group=_("Kafka"),
        subgroup=_("集群管理"),
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

    KAFKA_DESTROY = ActionMeta(
        id="kafka_destroy",
        name=_("Kafka 集群删除"),
        name_en="kafka_destroy",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.KAFKA],
        group=_("Kafka"),
        subgroup=_("集群管理"),
    )

    HDFS_APPLY = ActionMeta(
        id="hdfs_apply",
        name=_("HDFS 集群部署"),
        name_en="hdfs_apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("HDFS"),
        subgroup=_("集群管理"),
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

    HDFS_SCALE_UP = ActionMeta(
        id="hdfs_scale_up",
        name=_("HDFS 集群扩容"),
        name_en="hdfs_scale_up",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.HDFS],
        group=_("HDFS"),
        subgroup=_("集群管理"),
    )

    HDFS_SHRINK = ActionMeta(
        id="hdfs_shrink",
        name=_("HDFS 集群缩容"),
        name_en="hdfs_shrink",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.HDFS],
        group=_("HDFS"),
        subgroup=_("集群管理"),
    )

    HDFS_REBOOT = ActionMeta(
        id="hdfs_reboot",
        name=_("HDFS 集群节点重启"),
        name_en="hdfs_reboot",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.HDFS],
        group=_("HDFS"),
        subgroup=_("集群管理"),
    )

    HDFS_REPLACE = ActionMeta(
        id="hdfs_replace",
        name=_("HDFS 集群实例替换"),
        name_en="hdfs_replace",
        type="execute",
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

    HDFS_DESTROY = ActionMeta(
        id="hdfs_destroy",
        name=_("HDFS 集群删除"),
        name_en="hdfs_destroy",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.HDFS],
        group=_("HDFS"),
        subgroup=_("集群管理"),
    )

    PULSAR_APPLY = ActionMeta(
        id="pulsar_apply",
        name=_("Pulsar 集群部署"),
        name_en="pulsar_apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("Pulsar"),
        subgroup=_("集群管理"),
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

    PULSAR_SCALE_UP = ActionMeta(
        id="pulsar_scale_up",
        name=_("Pulsar 集群扩容"),
        name_en="pulsar_scale_up",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.PULSAR],
        group=_("Pulsar"),
        subgroup=_("集群管理"),
    )

    PULSAR_SHRINK = ActionMeta(
        id="pulsar_shrink",
        name=_("Pulsar 集群缩容"),
        name_en="pulsar_shrink",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.PULSAR],
        group=_("Pulsar"),
        subgroup=_("集群管理"),
    )

    PULSAR_REBOOT = ActionMeta(
        id="pulsar_reboot",
        name=_("Pulsar 集群节点重启"),
        name_en="pulsar_reboot",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.PULSAR],
        group=_("Pulsar"),
        subgroup=_("集群管理"),
    )

    PULSAR_REPLACE = ActionMeta(
        id="pulsar_replace",
        name=_("Pulsar 集群实例替换"),
        name_en="pulsar_replace",
        type="execute",
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

    PULSAR_DESTROY = ActionMeta(
        id="pulsar_destroy",
        name=_("Pulsar 集群删除"),
        name_en="pulsar_destroy",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.PULSAR],
        group=_("Pulsar"),
        subgroup=_("集群管理"),
    )

    RIAK_APPLY = ActionMeta(
        id="riak_apply",
        name=_("Riak 集群部署"),
        name_en="riak_apply",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.BUSINESS],
        group=_("Riak"),
        subgroup=_("集群管理"),
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

    RIAK_SCALE_UP = ActionMeta(
        id="riak_scale_up",
        name=_("Riak 集群扩容"),
        name_en="riak_scale_up",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.RIAK],
        group=_("Riak"),
        subgroup=_("集群管理"),
    )

    RIAK_SHRINK = ActionMeta(
        id="riak_shrink",
        name=_("Riak 集群缩容"),
        name_en="riak_shrink",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.RIAK],
        group=_("Riak"),
        subgroup=_("集群管理"),
    )

    RIAK_REBOOT = ActionMeta(
        id="riak_reboot",
        name=_("Riak 集群节点重启"),
        name_en="riak_reboot",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.RIAK],
        group=_("Riak"),
        subgroup=_("集群管理"),
    )

    RIAK_REPLACE = ActionMeta(
        id="riak_replace",
        name=_("Riak 集群实例替换"),
        name_en="riak_replace",
        type="execute",
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

    RIAK_DESTROY = ActionMeta(
        id="riak_destroy",
        name=_("Riak 集群删除"),
        name_en="riak_destroy",
        type="execute",
        related_actions=[DB_MANAGE.id],
        related_resource_types=[ResourceEnum.RIAK],
        group=_("Riak"),
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
        if cluster_type in [ClusterType.TenDBSingle, ClusterType.TenDBHA]:
            return cls.MYSQL_VIEW
        if cluster_type in ClusterType.redis_cluster_types():
            return cls.REDIS_VIEW
        return getattr(cls, f"{cluster_type.upper()}_VIEW")

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


_all_actions = {action.id: action for action in ActionEnum.__dict__.values() if isinstance(action, ActionMeta)}
