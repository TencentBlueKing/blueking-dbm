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
from backend.flow.engine.controller.spider import SpiderController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import ResourceSpecBaseSerializer
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.builders.tendbcluster.base import (
    BaseTendbTicketFlowBuilder,
    TendbBaseOperateDetailSerializer,
    TendbBaseOperateResourceParamBuilder,
)
from backend.ticket.constants import TicketType


class TenDBMigrateUpgradeSerializer(TendbBaseOperateDetailSerializer):
    class InfoSerializer(serializers.Serializer):
        class VersionModelSerializer(serializers.Serializer):
            db_version = serializers.CharField(help_text=_("DB版本"), required=False)
            pkg_name = serializers.CharField(help_text=_("包名称"), required=False)
            charset = serializers.CharField(help_text=_("字符集"), required=False)
            db_module_name = serializers.CharField(help_text=_("DB模块名称"), required=False)

        class ResourceModelSerializer(serializers.Serializer):
            backend_group = ResourceSpecBaseSerializer(help_text=_("主机规格信息"))

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        pkg_id = serializers.IntegerField(help_text=_("目标版本包ID"))
        new_db_module_id = serializers.IntegerField(help_text=_("数据库模块ID"), required=False)
        remote_shard_num = serializers.IntegerField(help_text=_("每组机器分片数"), required=False)
        resource_spec = ResourceModelSerializer(help_text=_("资源规格参数"), required=False)
        old_nodes = serializers.JSONField(help_text=_("旧节点信息集合"))
        current_version = VersionModelSerializer(help_text=_("当前版本信息"), required=False)
        target_version = VersionModelSerializer(help_text=_("目标版本信息"), required=False)

    infos = serializers.ListField(help_text=_("单据信息"), child=InfoSerializer())
    need_checksum = serializers.BooleanField(help_text=_("是否需要数据校验"), default=True, required=False)
    backup_source = serializers.ChoiceField(help_text=_("备份源"), choices=MySQLBackupSource.get_choices())
    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL
    )


class TenDBMigrateUpgradeParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.tendbcluster_remote_upgrade


class TenDBMigrateUpgradeResourceParamBuilder(TendbBaseOperateResourceParamBuilder):
    def format(self):
        self.patch_info_common_affinity("backend_group")

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        for info in next_flow.details["ticket_data"]["infos"]:
            # 格式化规格信息
            info["resource_spec"]["remote"] = info["resource_spec"]["master"]
            info["remote_group"] = info.pop("backend_group")

        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(
    TicketType.TENDBCLUSTER_MIGRATE_UPGRADE, is_apply=True, is_recycle=True, iam=ActionEnum.TENDBCLUSTER_MANAGE
)
class TenDBMigrateUpgradeFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TenDBMigrateUpgradeSerializer
    inner_flow_builder = TenDBMigrateUpgradeParamBuilder
    inner_flow_name = _("TenDB Cluster 存储层迁移升级")
    resource_batch_apply_builder = TenDBMigrateUpgradeResourceParamBuilder
    need_patch_recycle_host_details = True
    validator = None
