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
from backend.ticket.builders.tendbcluster.base import (
    BaseTendbTicketFlowBuilder,
    TendbBaseOperateDetailSerializer,
    TendbBaseOperateResourceParamBuilder,
)
from backend.ticket.constants import TicketType


class SpiderSlaveDestroyDetailSerializer(TendbBaseOperateDetailSerializer):
    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"), required=False, default=True)
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())


class SpiderSlaveDestroyFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.destroy_tendb_slave_cluster


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_SPIDER_SLAVE_DESTROY, is_apply=True)
class SpiderSlaveApplyFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = SpiderSlaveDestroyDetailSerializer
    inner_flow_builder = SpiderSlaveDestroyFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 只读集群下架")
