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
from backend.ticket.constants import FlowType, TicketType
from backend.ticket.models import Flow

logger = logging.getLogger("root")


class CloudNginxReplaceDetailSerializer(serializers.Serializer):
    class NginxDetailSerializer(serializers.Serializer):
        host_infos = serializers.ListField(help_text=_("部署nginx服务主机信息"), child=serializers.DictField())

    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    old_nginx_id = serializers.IntegerField(help_text=_("替换的nginx id"))
    new_nginx = NginxDetailSerializer(help_text=_("nginx服务部署信息"))


class CloudNginxReplaceItsmParamBuilder(builders.ItsmParamBuilder):
    def format(self):
        pass


class CloudNginxReplaceFlowParamBuilder(BaseServiceOperateFlowParamBuilder):
    controller = CloudServiceController.nginx_replace_scene

    def format_ticket_data(self):
        self.ticket_data = self.patch_ticket_data(self.ticket_data, ExtensionType.NGINX.lower())


@builders.BuilderFactory.register(TicketType.CLOUD_NGINX_REPLACE)
class CloudNginxReplaceFlowBuilder(BaseCloudTicketFlowBuilder):
    serializer = CloudNginxReplaceDetailSerializer
    inner_flow_builder = CloudNginxReplaceFlowParamBuilder
    inner_flow_name = _("Nginx 服务替换")
    editable = False

    @property
    def need_itsm(self):
        return False
