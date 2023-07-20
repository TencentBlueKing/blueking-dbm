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

from backend.db_meta.models import AppCache, Cluster
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.spider.base import (
    BaseTendbTicketFlowBuilder,
    TendbBaseOperateDetailSerializer,
    TendbBaseOperateResourceParamBuilder,
)
from backend.ticket.constants import TicketType


class SpiderSlaveApplyDetailSerializer(TendbBaseOperateDetailSerializer):
    class SpiderNodesItemSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        spider_slave_ip_list = serializers.ListField(
            help_text=_("slave信息"), child=serializers.DictField(), required=False
        )
        resource_spec = serializers.JSONField(help_text=_("资源规格参数"), required=False)

    infos = serializers.ListSerializer(help_text=_("扩容信息"), child=SpiderNodesItemSerializer())
    # 暂时不清楚该单据是否支持资源池，所以默认手动输入
    ip_source = serializers.ChoiceField(
        help_text=_("机器导入类型"), choices=IpSource.get_choices(), required=False, default=IpSource.MANUAL_INPUT
    )


class SpiderSlaveApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.spider_slave_cluster_apply_scene

    def format_ticket_data(self):
        # 补充从域名
        cluster_ids = [info["cluster_id"] for info in self.ticket_data["infos"]]
        cluster_id__name = {cluster.id: cluster.name for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        db_app_abbr = AppCache.objects.get(bk_biz_id=self.ticket.bk_biz_id).db_app_abbr
        for info in self.ticket_data["infos"]:
            info.update(slave_domain=f"spider.slave-{cluster_id__name[info['cluster_id']]}.{db_app_abbr}.db")


class SpiderSlaveApplyResourceParamBuilder(TendbBaseOperateResourceParamBuilder):
    def post_callback(self):
        next_flow = self.ticket.next_flow()
        for info in next_flow.details["ticket_data"]["infos"]:
            # 格式化规格信息
            info["resource_spec"]["spider"] = info["resource_spec"].pop("spider_slave_ip_list")

        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_SPIDER_SLAVE_APPLY, is_apply=True)
class SpiderSlaveApplyFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = SpiderSlaveApplyDetailSerializer
    inner_flow_builder = SpiderSlaveApplyFlowParamBuilder
    inner_flow_name = _("spider-slave 集群添加")
    resource_batch_apply_builder = SpiderSlaveApplyResourceParamBuilder
