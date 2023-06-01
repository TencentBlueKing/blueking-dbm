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

from backend.ticket import builders
from backend.ticket.builders.spider.base import BaseTendbTicketFlowBuilder
from backend.ticket.builders.spider.tendb_master_slave_switch import TendbMasterSlaveSwitchDetailSerializer
from backend.ticket.constants import TicketType


class TendbMasterFailOverDetailSerializer(TendbMasterSlaveSwitchDetailSerializer):
    pass


class TendbMasterFailOverParamBuilder(builders.FlowParamBuilder):
    # controller = SpiderController.mysql_ha_master_fail_over_scene
    controller = None


@builders.BuilderFactory.register(TicketType.SPIDER_MASTER_FAIL_OVER)
class TendbMasterFailOverFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbMasterFailOverDetailSerializer
    inner_flow_builder = TendbMasterFailOverParamBuilder
    inner_flow_name = _("TendbCluster 主故障切换")

    @property
    def need_manual_confirm(self):
        return True
