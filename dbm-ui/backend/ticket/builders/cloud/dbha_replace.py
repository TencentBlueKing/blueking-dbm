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

from backend.flow.consts import CloudDBHATypeEnum
from backend.flow.engine.controller.cloud import CloudServiceController
from backend.ticket import builders
from backend.ticket.builders.cloud.base import BaseServiceOperateFlowParamBuilder
from backend.ticket.builders.common.bigdata import BaseCloudTicketFlowBuilder
from backend.ticket.constants import FlowType, TicketType
from backend.ticket.models import Flow

logger = logging.getLogger("root")


class CloudDBHAReplaceDetailSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))

    old_gm_id = serializers.IntegerField(help_text=_("被替换旧DBHA-GM服务ID"), required=False)
    new_gm = serializers.DictField(help_text=_("替换后的新的DBHA-GM服务信息"), required=False)

    old_agent_id = serializers.IntegerField(help_text=_("被替换旧DBHA-AGENT服务ID"), required=False)
    new_agent = serializers.DictField(help_text=_("替换后的新的DBHA-AGENT服务信息"), required=False)

    def validate(self, attrs):
        if attrs.get("old_agent_id") and attrs.get("old_gm_id"):
            raise serializers.ValidationError(_("不允许同时对agent和gm进行替换"))

        return attrs


class CloudDBHAReplaceFlowParamBuilder(BaseServiceOperateFlowParamBuilder):
    controller = CloudServiceController.dbha_replace_scene

    def format_ticket_data(self):
        if self.ticket_data.get("old_gm_id"):
            self.ticket_data = self.patch_ticket_data(self.ticket_data, CloudDBHATypeEnum.GM.lower())
            # agent不被清空，所以移除掉相关信息
            self.ticket_data["dbha"]["agent"] = []
            self.ticket_data["old_agent"] = {"host_infos": []}
        else:
            self.ticket_data = self.patch_ticket_data(self.ticket_data, CloudDBHATypeEnum.AGENT.lower())
            self.ticket_data["dbha"]["gm"] = []
            self.ticket_data["old_gm"] = {"host_infos": []}


@builders.BuilderFactory.register(TicketType.CLOUD_DBHA_REPLACE)
class CloudDBHAReplaceFlowBuilder(BaseCloudTicketFlowBuilder):
    serializer = CloudDBHAReplaceDetailSerializer
    inner_flow_builder = CloudDBHAReplaceFlowParamBuilder
    inner_flow_name = _("DBHA 服务替换")

    @property
    def need_itsm(self):
        return False
