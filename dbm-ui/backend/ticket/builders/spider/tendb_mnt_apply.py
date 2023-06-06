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
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.spider.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class TendbMNTApplyDetailSerializer(TendbBaseOperateDetailSerializer):
    class MNTApplySerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        spider_ip_list = serializers.ListField(help_text=_("临时节点信息"), child=serializers.DictField())

    infos = serializers.ListField(help_text=_("添加spider临时节点信息"), child=MNTApplySerializer())

    def validate(self, attrs):
        # super().validate(attrs)
        return attrs


class TendbMNTApplyParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.add_spider_mnt_scene

    def format_ticket_data(self):
        cluster_ids = [info["cluster_id"] for info in self.ticket_data["infos"]]
        cluster_id__domain = {
            cluster.id: cluster.immute_domain for cluster in Cluster.objects.filter(id__in=cluster_ids)
        }
        for info in self.ticket_data["infos"]:
            info.update(immutable_domain=cluster_id__domain[info["cluster_id"]])


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_SPIDER_MNT_APPLY, is_apply=True)
class TendbMNTApplyFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbMNTApplyDetailSerializer
    inner_flow_builder = TendbMNTApplyParamBuilder
    inner_flow_name = _("TendbCluster 添加临时节点")

    @property
    def need_itsm(self):
        return False
