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
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.builders.mysql.mysql_cluster_standardize import MySQLClusterStandardizeFlowParamBuilder
from backend.ticket.constants import FlowType, TicketType
from backend.ticket.models import Flow


class MySQLRollbackSwitchDetailSerializer(MySQLBaseOperateDetailSerializer):
    class RollbackSwitchSerializer(serializers.Serializer):
        source_cluster_id = serializers.IntegerField(help_text=_("回档源集群ID"))
        destination_cluster_id = serializers.IntegerField(help_text=_("回档目标集群ID"))

    infos = serializers.ListSerializer(help_text=_("回档切换信息"), child=RollbackSwitchSerializer())


class MySQLRollbackSwitchFlowParamBuilder(builders.FlowParamBuilder):
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


class MySQLRollbackSwitchStandardizeParamBuilder(MySQLClusterStandardizeFlowParamBuilder):
    """切换执行成功后，对源集群和回档目标集群执行集群标准化（部署二进制/推送配置等）"""

    def format_ticket_data(self):
        # 标准化对象为源集群和切换后的新集群(回档目标)，参数与集群标准化单据的默认值保持一致
        self.ticket_data.update(
            bk_biz_id=self.ticket.bk_biz_id,
            cluster_ids=[
                cluster_id
                for info in self.ticket_data["infos"]
                for cluster_id in (info["source_cluster_id"], info["destination_cluster_id"])
            ],
            with_deploy_binary=True,
            with_push_config=True,
            with_cc_standardize=True,
            with_instance_standardize=False,
        )


@builders.BuilderFactory.register(TicketType.MYSQL_ROLLBACK_SWITCH, is_apply=True, iam=ActionEnum.MYSQL_ROLLBACK)
class MySQLRollbackSwitchFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLRollbackSwitchDetailSerializer
    inner_flow_builder = MySQLRollbackSwitchFlowParamBuilder
    inner_flow_name = _("MySQL 构造回档切换执行")

    def custom_ticket_flows(self):
        """单据审批(可选) → 构造回档切换执行 → 源集群与目标集群标准化"""
        return [
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=self.inner_flow_builder(self.ticket).get_params(),
                flow_alias=self.inner_flow_name,
                retry_type=self.retry_type,
            ),
            # 切换成功后对源集群和回档目标集群做标准化，补齐二进制/配置/监控等周边
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=MySQLRollbackSwitchStandardizeParamBuilder(self.ticket).get_params(),
                flow_alias=_("MySQL集群标准化"),
                retry_type=self.retry_type,
            ),
        ]

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = cls._add_itsm_pause_describe(flow_desc=[], flow_config_map=flow_config_map)
        flow_desc.extend([cls.inner_flow_name, _("MySQL集群标准化")])
        return flow_desc
