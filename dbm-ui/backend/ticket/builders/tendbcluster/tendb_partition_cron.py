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

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.models import AppCache
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import MySQLBaseOperateDetailSerializer
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder
from backend.ticket.constants import TicketType


class SpiderPartitionCronDetailSerializer(MySQLBaseOperateDetailSerializer):
    class PartitionInfoSerializer(serializers.Serializer):
        ip = serializers.CharField(help_text=_("服务器IP"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        file_name = serializers.CharField(help_text=_("分区文件名"))

    infos = serializers.ListSerializer(help_text=_("分区信息"), child=PartitionInfoSerializer())


class SpiderPartitionCronParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.spider_partition_cron

    def format_ticket_data(self):
        app = AppCache.objects.get(bk_biz_id=self.ticket_data["bk_biz_id"])
        self.ticket_data.update(bk_biz_name=app.bk_biz_name, db_app_abbr=app.db_app_abbr)


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_PARTITION_CRON)
class SpiderPartitionCronFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = SpiderPartitionCronDetailSerializer
    inner_flow_builder = SpiderPartitionCronParamBuilder
    inner_flow_name = _("分区管理定时任务执行")
    default_need_itsm = False
    default_need_manual_confirm = False
