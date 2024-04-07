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

from backend.flow.consts import CloudDBHATypeEnum
from backend.flow.engine.controller.cloud import CloudServiceController
from backend.ticket import builders
from backend.ticket.builders.cloud.base import BaseServiceOperateFlowParamBuilder
from backend.ticket.builders.common.bigdata import BaseCloudTicketFlowBuilder
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class CloudDBHAReloadDetailSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    gm_ids = serializers.ListField(help_text=_("重装的GM ID列表"), child=serializers.IntegerField())
    agent_ids = serializers.ListField(help_text=_("重装的AGENT ID列表"), child=serializers.IntegerField())


class CloudDBHAReloadFlowParamBuilder(BaseServiceOperateFlowParamBuilder):
    controller = CloudServiceController.dbha_reload_scene

    def format_ticket_data(self):
        self.ticket_data = self.patch_ticket_data(self.ticket_data, CloudDBHATypeEnum.GM)
        self.ticket_data = self.patch_ticket_data(self.ticket_data, CloudDBHATypeEnum.AGENT, keep=True)
        self.padding_dbha_type(self.ticket_data)


@builders.BuilderFactory.register(TicketType.CLOUD_DBHA_RELOAD)
class CloudDBHAReloadFlowBuilder(BaseCloudTicketFlowBuilder):
    serializer = CloudDBHAReloadDetailSerializer
    inner_flow_builder = CloudDBHAReloadFlowParamBuilder
    inner_flow_name = _("DBHA 服务重装")
    editable = False

    @property
    def need_itsm(self):
        return False
