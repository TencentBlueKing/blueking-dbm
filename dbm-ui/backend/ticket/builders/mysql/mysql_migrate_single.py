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
from rest_framework import serializers

from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.mysql import MySQLController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder, HostInfoSerializer
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.builders.mysql.base import BaseMySQLSingleTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class MysqlMigrateSingleDetailSerializer(MySQLBaseOperateDetailSerializer):
    class MigrateInfoSerializer(serializers.Serializer):
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
        resource_spec = serializers.JSONField(help_text=_("资源规格"))
        old_orphan = HostInfoSerializer(help_text=_("旧孤儿节点"))
        # 前端参数展示
        related_cluster_infos = serializers.JSONField(help_text=_("关联集群信息"), required=False)

    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), required=False, default=IpSource.RESOURCE_POOL
    )
    infos = serializers.ListField(help_text=_("迁移主从信息"), child=MigrateInfoSerializer())
    orphan_restore_type = serializers.CharField(help_text=_("迁移类型"))
    backup_source = serializers.ChoiceField(help_text=_("备份源"), choices=MySQLBackupSource.get_choices())
    # 前端参数展示
    migrate_type = serializers.CharField(help_text=_("迁移类型"), required=False)

    def validate(self, attrs):
        return super().validate(attrs)


class MysqlMigrateSingleParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_migrate_single_scene


class MysqlMigrateSingleResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        self.patch_info_common_affinity(role="bk_new_orphan")


@builders.BuilderFactory.register(
    TicketType.MYSQL_MIGRATE_SINGLE, is_apply=True, is_recycle=True, iam=ActionEnum.MYSQL_MANAGE
)
class MysqlMigrateSingleFlowBuilder(BaseMySQLSingleTicketFlowBuilder):
    serializer = MysqlMigrateSingleDetailSerializer
    inner_flow_builder = MysqlMigrateSingleParamBuilder
    resource_batch_apply_builder = MysqlMigrateSingleResourceParamBuilder
    need_patch_recycle_cluster_details = True
    validator = MySQLController.mysql_migrate_single_scene.validator
