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

from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import DisplayInfoSerializer
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class MysqlLocalUpgradeDetailSerializer(MySQLBaseOperateDetailSerializer):
    class InfoSerializer(DisplayInfoSerializer):
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField(), min_length=1)
        pkg_id = serializers.IntegerField(help_text=_("目标版本包ID"))

    infos = serializers.ListField(help_text=_("单据信息"), child=InfoSerializer())
    force = serializers.BooleanField(help_text=_("是否强制执行"), required=False, default=False)


class MysqlLocalUpgradeParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_local_upgrade_scene


@builders.BuilderFactory.register(TicketType.MYSQL_LOCAL_UPGRADE)
class MysqlLocalUpgradeFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MysqlLocalUpgradeDetailSerializer
    inner_flow_builder = MysqlLocalUpgradeParamBuilder
