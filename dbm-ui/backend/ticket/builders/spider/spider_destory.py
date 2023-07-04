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

from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.spider.base import BaseTendbTicketFlowBuilder, TendbClustersTakeDownDetailsSerializer
from backend.ticket.constants import TicketType


class TendbDestroyDetailSerializer(TendbClustersTakeDownDetailsSerializer):
    pass


class TendbDestroyFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.spider_cluster_disable_scene


@builders.BuilderFactory.register(TicketType.TENDB_CLUSTER_DESTROY)
class TendbDestroyFlowBuilder(BaseTendbTicketFlowBuilder):

    serializer = TendbDestroyDetailSerializer
    inner_flow_builder = TendbDestroyFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 下架执行")
