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

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.db_proxy.constants import ExtensionType
from backend.db_proxy.models import DBExtension
from backend.flow.engine.controller.cloud import CloudServiceController
from backend.ticket import builders
from backend.ticket.builders.cloud.base import BaseServiceOperateFlowParamBuilder
from backend.ticket.builders.common.bigdata import BaseCloudTicketFlowBuilder
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class CloudDNSReduceDetailSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    old_dns_ids = serializers.ListField(help_text=_("裁撤的DNS列表"), child=serializers.IntegerField())

    def validate(self, attrs):
        dns_extensions = DBExtension.get_extension_in_cloud(attrs["bk_cloud_id"], ExtensionType.DNS)
        dns_ids = [dns.id for dns in dns_extensions]
        if set(attrs["old_dns_ids"]) == set(dns_ids):
            raise serializers.ValidationError(_("请至少保证一个dns服务存活"))

        return attrs


class CloudDNSReduceFlowParamBuilder(BaseServiceOperateFlowParamBuilder):
    controller = CloudServiceController.dns_reduce_scene

    def format_ticket_data(self):
        self.ticket_data = self.patch_ticket_data(self.ticket_data, ExtensionType.DNS.lower())


@builders.BuilderFactory.register(TicketType.CLOUD_DNS_REDUCE)
class CloudDNSReduceFlowBuilder(BaseCloudTicketFlowBuilder):
    serializer = CloudDNSReduceDetailSerializer
    inner_flow_builder = CloudDNSReduceFlowParamBuilder
    inner_flow_name = _("DNS 服务裁撤")
    editable = False

    @property
    def need_itsm(self):
        return False
