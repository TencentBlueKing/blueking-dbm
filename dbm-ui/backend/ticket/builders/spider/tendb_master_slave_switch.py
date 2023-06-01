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

from backend.ticket import builders
from backend.ticket.builders.common.base import HostInfoSerializer
from backend.ticket.builders.spider.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class TendbMasterSlaveSwitchDetailSerializer(TendbBaseOperateDetailSerializer):
    class InfoSerializer(serializers.Serializer):
        master_ip = HostInfoSerializer(help_text=_("主库 IP"))
        slave_ip = HostInfoSerializer(help_text=_("从库 IP"))
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())

    infos = serializers.ListField(help_text=_("单据信息"), child=InfoSerializer())
    is_check_proc = serializers.BooleanField(help_text=_("是否检测连接"))
    is_check_delay = serializers.BooleanField(help_text=_("是否检测数据同步延时情况"))
    is_check_checksum = serializers.BooleanField(help_text=_("是否检测历史数据检验结果"))

    def validate(self, attrs):
        # super().validate(attrs)
        return attrs


class TendbMasterSlaveSwitchParamBuilder(builders.FlowParamBuilder):
    # controller = SpiderController.mysql_ha_switch_scene
    controller = None


@builders.BuilderFactory.register(TicketType.SPIDER_MASTER_SLAVE_SWITCH)
class TendbMasterSlaveSwitchFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbMasterSlaveSwitchDetailSerializer
    inner_flow_builder = TendbMasterSlaveSwitchParamBuilder
    inner_flow_name = _("TendbCluster 主从互换执行")

    @property
    def need_manual_confirm(self):
        return True
