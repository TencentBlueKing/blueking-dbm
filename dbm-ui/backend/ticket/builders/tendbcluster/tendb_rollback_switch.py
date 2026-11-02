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

from backend.db_meta.models import Cluster
from backend.flow.engine.controller.mysql import MySQLController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class TendbRollbackSwitchDetailSerializer(TendbBaseOperateDetailSerializer):
    class RollbackSwitchSerializer(serializers.Serializer):
        source_cluster_id = serializers.IntegerField(help_text=_("回档源集群ID"))
        destination_cluster_id = serializers.IntegerField(help_text=_("回档目标集群ID"))

    infos = serializers.ListSerializer(help_text=_("回档切换信息"), child=RollbackSwitchSerializer())


class TendbRollbackSwitchFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_rollback_switch_scene

    def format_ticket_data(self):
        # 云区域和模块信息与源集群保持一致，单据由新机回档单据自动发起时会在details中带上，
        # 手工提单时在此补齐，避免流程侧取不到这两个参数
        if not self.ticket_data.get("bk_cloud_id") or not self.ticket_data.get("module"):
            source_cluster = Cluster.objects.get(id=self.ticket_data["infos"][0]["source_cluster_id"])
            self.ticket_data.update(
                bk_cloud_id=self.ticket_data.get("bk_cloud_id") or source_cluster.bk_cloud_id,
                module=self.ticket_data.get("module") or source_cluster.db_module_id,
            )


@builders.BuilderFactory.register(
    TicketType.TENDBCLUSTER_ROLLBACK_SWITCH, is_apply=True, iam=ActionEnum.TENDBCLUSTER_ROLLBACK
)
class TendbRollbackSwitchFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbRollbackSwitchDetailSerializer
    inner_flow_builder = TendbRollbackSwitchFlowParamBuilder
    inner_flow_name = _("TenDBCluster 构造回档切换执行")
