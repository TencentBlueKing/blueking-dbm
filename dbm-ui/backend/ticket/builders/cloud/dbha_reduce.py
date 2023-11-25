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
from backend.flow.consts import CloudDBHATypeEnum
from backend.flow.engine.controller.cloud import CloudServiceController
from backend.ticket import builders
from backend.ticket.builders.cloud.base import BaseServiceOperateFlowParamBuilder
from backend.ticket.builders.common.bigdata import BaseCloudTicketFlowBuilder
from backend.ticket.constants import FlowType, TicketType
from backend.ticket.models import Flow

logger = logging.getLogger("root")


class CloudDBHAReduceDetailSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    old_gm_ids = serializers.ListField(
        help_text=_("裁撤的DBHA-GM列表"), child=serializers.IntegerField(), required=False, default=[]
    )
    old_agent_ids = serializers.ListField(
        help_text=_("裁撤的DBHA-AGENT列表"), child=serializers.IntegerField(), required=False, default=[]
    )

    def validate(self, attrs):
        dbha_extensions = DBExtension.get_extension_in_cloud(attrs["bk_cloud_id"], ExtensionType.DBHA)
        gm_ids = [dbha.id for dbha in dbha_extensions if dbha.details["dbha_type"] == CloudDBHATypeEnum.GM]
        agent_ids = [dbha.id for dbha in dbha_extensions if dbha.details["dbha_type"] == CloudDBHATypeEnum.AGENT]

        if set(attrs["old_agent_ids"]) == set(agent_ids) or set(attrs["old_gm_ids"]) == set(gm_ids):
            raise serializers.ValidationError(_("请至少保证一个agent/gm存活"))

        return attrs


class CloudDBHAReduceFlowParamBuilder(BaseServiceOperateFlowParamBuilder):
    controller = CloudServiceController.dbha_reduce_scene

    def format_ticket_data(self):
        self.ticket_data = self.patch_ticket_data(self.ticket_data, CloudDBHATypeEnum.GM.lower())
        self.ticket_data = self.patch_ticket_data(self.ticket_data, CloudDBHATypeEnum.AGENT.lower(), keep=True)


@builders.BuilderFactory.register(TicketType.CLOUD_DBHA_REDUCE)
class CloudDBHAReduceFlowBuilder(BaseCloudTicketFlowBuilder):
    serializer = CloudDBHAReduceDetailSerializer
    inner_flow_builder = CloudDBHAReduceFlowParamBuilder
    inner_flow_name = _("DBHA 服务裁撤")
    editable = False

    @property
    def need_itsm(self):
        return False
