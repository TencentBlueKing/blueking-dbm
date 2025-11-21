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

from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLHATicketFlowBuilder
from backend.ticket.builders.mysql.mysql_proxy_switch import (
    MysqlProxySwitchDetailSerializer,
    MysqlProxySwitchResourceParamBuilder,
)
from backend.ticket.constants import FlowRetryType, TicketType


class MysqlProxyConfChangeDetailSerializer(MysqlProxySwitchDetailSerializer):
    pass


class MysqlProxyConfChangeParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_proxy_switch_for_extend_scene
    validator = MySQLController.mysql_proxy_switch_for_extend_scene.validator


class MysqlProxyConfChangeResourceParamBuilder(MysqlProxySwitchResourceParamBuilder):
    pass


@builders.BuilderFactory.register(TicketType.MYSQL_PROXY_CONF_CHANGE, is_apply=True, is_recycle=True)
class MysqlProxyConfChangeFlowBuilder(BaseMySQLHATicketFlowBuilder):
    need_patch_recycle_host_details = True
    need_patch_machine_details = True
    retry_type = FlowRetryType.MANUAL_RETRY
    serializer = MysqlProxyConfChangeDetailSerializer
    inner_flow_builder = MysqlProxyConfChangeParamBuilder
    resource_batch_apply_builder = MysqlProxyConfChangeResourceParamBuilder
