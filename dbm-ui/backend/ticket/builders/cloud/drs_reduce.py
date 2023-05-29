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

from backend.db_proxy.constants import ExtensionType
from backend.db_proxy.models import DBExtension
from backend.flow.engine.controller.cloud import CloudServiceController
from backend.ticket import builders
from backend.ticket.builders.cloud.base import BaseServiceOperateFlowParamBuilder
from backend.ticket.builders.common.bigdata import BaseCloudTicketFlowBuilder
from backend.ticket.constants import FlowType, TicketType
from backend.ticket.models import Flow

logger = logging.getLogger("root")


class CloudDRSReduceDetailSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    old_drs_ids = serializers.ListField(help_text=_("裁撤的drs列表"), child=serializers.IntegerField())

    def validate(self, attrs):
        drs_extensions = DBExtension.get_extension_in_cloud(attrs["bk_cloud_id"], ExtensionType.DRS)
        drs_ids = [drs.id for drs in drs_extensions]
        if set(attrs["old_drs_ids"]) == set(drs_ids):
            raise serializers.ValidationError(_("请至少保证一个drs服务存活"))

        return attrs


class CloudDRSReduceFlowParamBuilder(BaseServiceOperateFlowParamBuilder):
    controller = CloudServiceController.drs_reduce_scene

    def format_ticket_data(self):
        self.ticket_data = self.patch_ticket_data(self.ticket_data, ExtensionType.DRS.lower())


@builders.BuilderFactory.register(TicketType.CLOUD_DRS_REDUCE)
class CloudDRSReduceFlowBuilder(BaseCloudTicketFlowBuilder):
    serializer = CloudDRSReduceDetailSerializer
    inner_flow_builder = CloudDRSReduceFlowParamBuilder
    inner_flow_name = _("DRS 服务裁撤")

    @property
    def need_itsm(self):
        return False
