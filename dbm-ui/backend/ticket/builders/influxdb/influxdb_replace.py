# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸 (Blueking) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

import logging

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.flow.engine.controller.influxdb import InfluxdbController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import (
    BaseInfluxDBTicketFlowBuilder,
    BigDataReplaceDetailSerializer,
    BigDataReplaceResourceParamBuilder,
)
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class InfluxDBReplaceDetailSerializer(BigDataReplaceDetailSerializer):
    cluster_id = serializers.IntegerField(required=False)


class InfluxDBReplaceFlowParamBuilder(builders.FlowParamBuilder):
    controller = InfluxdbController.influxdb_replace_scene


class InfluxDBResourceParamBuilder(BigDataReplaceResourceParamBuilder):
    def format(self):
        # 默认认为替换的一批influxdb是同一云区域
        self.ticket_data["bk_cloud_id"] = self.ticket_data["old_nodes"]["influxdb"][0]["bk_cloud_id"]


@builders.BuilderFactory.register(TicketType.INFLUXDB_REPLACE, is_apply=True)
class InfluxDBReplaceFlowBuilder(BaseInfluxDBTicketFlowBuilder):
    serializer = InfluxDBReplaceDetailSerializer
    inner_flow_builder = InfluxDBReplaceFlowParamBuilder
    inner_flow_name = _("InfluxDB 实例替换")
    resource_apply_builder = InfluxDBResourceParamBuilder
