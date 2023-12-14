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
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, TicketType


class TenClusterStandardizeDetailSerializer(TendbBaseOperateDetailSerializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"))

    def validate(self, attrs):
        return attrs


class TendbClusterStandardizeFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.migrate_spider_cluster_from_gcs


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_STANDARDIZE)
class MysqlStandardizeFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TenClusterStandardizeDetailSerializer
    inner_flow_builder = TendbClusterStandardizeFlowParamBuilder
    inner_flow_name = _("TendbCluster集群标准化")
    retry_type = FlowRetryType.MANUAL_RETRY
