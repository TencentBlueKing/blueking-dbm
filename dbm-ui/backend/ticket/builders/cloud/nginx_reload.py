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

from backend.db_proxy.models import DBExtension
from backend.flow.engine.controller.cloud import CloudServiceController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import BaseCloudTicketFlowBuilder
from backend.ticket.constants import FlowType, TicketType
from backend.ticket.models import Flow

logger = logging.getLogger("root")


class CloudNginxReloadDetailSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    nginx_id = serializers.IntegerField(help_text=_("重装的nginx id"))


class CloudNginxReloadItsmParamBuilder(builders.ItsmParamBuilder):
    def format(self):
        pass


class CloudNginxReloadFlowParamBuilder(builders.FlowParamBuilder):
    controller = CloudServiceController.nginx_reload_scene

    def format_ticket_data(self):
        # 目前nginx就一台，默认全部重启
        extension_info = DBExtension.get_extension_info_in_cloud(bk_cloud_id=self.ticket_data["bk_cloud_id"])
        self.ticket_data.update(extension_info)


@builders.BuilderFactory.register(TicketType.CLOUD_NGINX_RELOAD)
class CloudNginxReloadFlowBuilder(BaseCloudTicketFlowBuilder):
    serializer = CloudNginxReloadDetailSerializer
    inner_flow_builder = CloudNginxReloadFlowParamBuilder
    inner_flow_name = _("Nginx 服务重装")

    @property
    def need_itsm(self):
        return False
