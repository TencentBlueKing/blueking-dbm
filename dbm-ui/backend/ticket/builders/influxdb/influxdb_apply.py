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

from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.db_meta.models import Group
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.influxdb import InfluxdbController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import BaseInfluxDBTicketFlowBuilder, BigDataDetailsSerializer
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class InfluxDBApplyDetailSerializer(BigDataDetailsSerializer):
    city_code = serializers.CharField(
        help_text=_("城市代码"), required=False, allow_blank=True, allow_null=True, default=""
    )
    db_version = serializers.CharField(help_text=_("版本号"))
    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    port = serializers.IntegerField(help_text=_("端口"))
    group_id = serializers.IntegerField(help_text=_("分组ID"))
    group_name = serializers.CharField(help_text=_("分组名字"), required=False)
    resource_spec = serializers.JSONField(help_text=_("资源规格"), required=False)
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))

    def validate(self, attrs):
        # 判断主机是否来自手工输入，从资源池拿到的主机不需要校验
        if attrs["ip_source"] == IpSource.RESOURCE_POOL:
            return attrs

        # 判断主机是否都来自空闲机
        super().validate_hosts_from_idle_pool(bk_biz_id=self.context["bk_biz_id"], nodes=attrs["nodes"])

        # 判断机器是否已经存在于db_meta中
        super().validate_hosts_not_in_db_meta(nodes=attrs["nodes"])

        return attrs


class InfluxDBApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = InfluxdbController.influxdb_apply_scene

    def format_ticket_data(self):
        # TODO: 暂时先生成随机的账号密码
        self.ticket_data.update(
            {
                "username": get_random_string(8),
                "password": get_random_string(16),
                "group_name": Group.objects.get(pk=self.ticket_data["group_id"]).name,
            }
        )


class InfluxApplyDBResourceParamBuilder(builders.ResourceApplyParamBuilder):
    pass


@builders.BuilderFactory.register(TicketType.INFLUXDB_APPLY)
class InfluxDBApplyFlowBuilder(BaseInfluxDBTicketFlowBuilder):
    serializer = InfluxDBApplyDetailSerializer
    inner_flow_builder = InfluxDBApplyFlowParamBuilder
    inner_flow_name = _("InfluxDB 实例部署")
    resource_apply_builder = InfluxApplyDBResourceParamBuilder
