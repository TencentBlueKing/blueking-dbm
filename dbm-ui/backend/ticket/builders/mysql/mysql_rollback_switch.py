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
from typing import Dict, List

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
    """切换执行成功后，对源集群和回档目标集群执行集群标准化（部署二进制/推送配置等）

    切换流程会互换源集群与回档目标集群的域名等集群信息（MySQLDBMeta.tendb_exchange_domain），
    建单时 patch_cluster_details 补充到 details["clusters"] 的集群快照在标准化执行时已经过期，
    因此需要在节点真正执行前重新执行一次 patch_cluster_details，再用最新的集群信息刷新流程参数。
    """

    @staticmethod
    def get_standardize_cluster_ids(infos: List[Dict]) -> List[int]:
        """标准化对象为源集群和回档目标集群，去重并保持单据中的顺序"""
        cluster_ids = []
        for info in infos:
            for cluster_id in (info["source_cluster_id"], info["destination_cluster_id"]):
                if cluster_id not in cluster_ids:
                    cluster_ids.append(cluster_id)
        return cluster_ids

    def format_ticket_data(self):
        # 参数与集群标准化单据的默认值保持一致；集群信息先按建单时的数据占位，
        # 实际执行前由 pre_callback 重新 patch_cluster_details 后覆盖
        self.ticket_data.update(
            bk_biz_id=self.ticket.bk_biz_id,
            cluster_ids=self.get_standardize_cluster_ids(self.ticket_data["infos"]),
            with_deploy_binary=True,
            with_push_config=True,
            with_cc_standardize=True,
            with_instance_standardize=False,
        )

    def pre_callback(self):
        """切换执行完成后，重新补充集群信息，再按最新的集群信息刷新标准化流程参数

        上一个节点已经完成源集群与回档目标集群的域名互换，
        建单时 patch_cluster_details 写入的集群快照（域名等）不再准确，
        这里重新执行一次 patch_cluster_details，并用它回写的集群信息覆盖标准化流程参数
        """
        self.ticket.refresh_from_db(fields=["details"])
        # 重新读 cluster 表补充集群信息，替换掉建单时的集群快照
        MySQLRollbackSwitchFlowBuilder(self.ticket).patch_cluster_details()
        self.ticket.save(update_fields=["details", "update_at"])

        cluster_ids = self.get_standardize_cluster_ids(self.ticket.details["infos"])
        if not cluster_ids:
            raise Exception(_("单据 infos 中未取到源集群/回档目标集群，无法执行集群标准化"))

        clusters = self.ticket.details.get("clusters") or {}
        # details 落库为 JSON 后字典的 key 是字符串，这里统一按 int 处理
        cluster_map = {int(cluster_id): cluster for cluster_id, cluster in clusters.items()}
        missing_cluster_ids = [cluster_id for cluster_id in cluster_ids if cluster_id not in cluster_map]
        if missing_cluster_ids:
            raise Exception(_("集群{}在集群表中不存在，无法执行集群标准化").format(missing_cluster_ids))

        bk_biz_ids = {cluster["bk_biz_id"] for cluster in cluster_map.values()}
        if len(bk_biz_ids) > 1:
            raise Exception(_("源集群与回档目标集群不属于同一业务，无法同时执行集群标准化: {}").format(sorted(bk_biz_ids)))

        # 标准化流程的 ticket_data 同样是建单时的快照，一并刷新成切换后的集群信息
        standardize_flow = self.ticket.current_flow()
        ticket_data = standardize_flow.details["ticket_data"]
        ticket_data.update(bk_biz_id=bk_biz_ids.pop(), cluster_ids=cluster_ids, clusters=clusters)
        standardize_flow.save(update_fields=["details"])


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
