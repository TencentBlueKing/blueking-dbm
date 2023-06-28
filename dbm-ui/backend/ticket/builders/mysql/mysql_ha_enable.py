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

from typing import List

from django.utils.translation import ugettext_lazy as _

from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLClustersTakeDownDetailsSerializer
from backend.ticket.constants import FlowRetryType, TicketType


class MysqlHAEnableDetailSerializer(MySQLClustersTakeDownDetailsSerializer):
    pass


class MysqlHAEnableFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_ha_enable_scene


@builders.BuilderFactory.register(TicketType.MYSQL_HA_ENABLE)
class MysqlHaEnableFlowBuilder(BaseMySQLTicketFlowBuilder):
    """Mysql下架流程的构建基类"""

    serializer = MysqlHAEnableDetailSerializer
    inner_flow_builder = MysqlHAEnableFlowParamBuilder
    inner_flow_name = _("MySQL高可用启用执行")
    retry_type = FlowRetryType.MANUAL_RETRY
