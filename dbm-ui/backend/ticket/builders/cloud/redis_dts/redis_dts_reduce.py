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
from backend.flow.engine.controller.cloud import CloudServiceController
from backend.ticket import builders
from backend.ticket.builders.cloud.base import BaseServiceOperateFlowParamBuilder
from backend.ticket.builders.common.bigdata import BaseCloudTicketFlowBuilder
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class CloudRedisDtsReduceDetailSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    old_redis_dts_ids = serializers.ListField(help_text=_("裁撤的redis_dts列表"), child=serializers.IntegerField())


class CloudRedisDtsReduceFlowParamBuilder(BaseServiceOperateFlowParamBuilder):
    controller = CloudServiceController.drs_reduce_scene

    def format_ticket_data(self):
        self.ticket_data = self.patch_ticket_data(self.ticket_data, ExtensionType.REDIS_DTS.lower())


@builders.BuilderFactory.register(TicketType.CLOUD_REDIS_DTS_SERVER_REDUCE)
class CloudRedisDtsReduceFlowBuilder(BaseCloudTicketFlowBuilder):
    serializer = CloudRedisDtsReduceDetailSerializer
    inner_flow_builder = CloudRedisDtsReduceFlowParamBuilder
    inner_flow_name = _("RedisDts 服务裁撤")
    editable = False

    @property
    def need_itsm(self):
        return False
