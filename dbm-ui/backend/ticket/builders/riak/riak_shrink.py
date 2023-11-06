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

import logging

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterPhase
from backend.db_meta.models import Cluster
from backend.flow.engine.controller.riak import RiakController
from backend.ticket import builders
from backend.ticket.builders.common.base import HostInfoSerializer
from backend.ticket.builders.riak.base import BaseRiakTicketFlowBuilder
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class RiakShrinkDetailSerializer(serializers.Serializer):
    cluster_id = serializers.Serializer(help_text=_("集群ID"))
    nodes = serializers.ListSerializer(help_text=_("缩容节点"), child=HostInfoSerializer())


class RiakShrinkFlowParamBuilder(builders.FlowParamBuilder):
    controller = RiakController.riak_cluster_scale_in_scene

    def format_ticket_data(self):
        cluster = Cluster.objects.get(id=self.ticket_data["cluster_id"])
        self.ticket_data["bk_cloud_id"] = cluster.bk_cloud_id


@builders.BuilderFactory.register(TicketType.RIAK_CLUSTER_SCALE_IN, phase=ClusterPhase.OFFLINE)
class RiakShrinkFlowBuilder(BaseRiakTicketFlowBuilder):
    serializer = RiakShrinkDetailSerializer
    inner_flow_builder = RiakShrinkFlowParamBuilder
    inner_flow_name = _("Riak 集群缩容")
