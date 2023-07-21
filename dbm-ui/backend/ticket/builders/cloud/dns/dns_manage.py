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

from backend.ticket import builders
from backend.ticket.builders.cloud.base import BaseServiceOperateFlowParamBuilder
from backend.ticket.builders.common.base import HostInfoSerializer
from backend.ticket.builders.common.bigdata import BaseCloudTicketFlowBuilder
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class CloudDNSManageDetailSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    dns_id = serializers.IntegerField(help_text=_("DNS服务器ID"))
    ip_list = serializers.ListSerializer(help_text=_("录入主机信息"), child=HostInfoSerializer())


class CloudDNSManageFlowParamBuilder(BaseServiceOperateFlowParamBuilder):
    controller = None


@builders.BuilderFactory.register(TicketType.CLOUD_DNS_MANAGE)
class CloudDNSManageFlowBuilder(BaseCloudTicketFlowBuilder):
    serializer = CloudDNSManageDetailSerializer
    inner_flow_builder = CloudDNSManageFlowParamBuilder
    inner_flow_name = _("DNS 主机录入管理")
