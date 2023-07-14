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

from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.common.base import HostInfoSerializer
from backend.ticket.builders.spider.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class TendbMasterSlaveSwitchDetailSerializer(TendbBaseOperateDetailSerializer):
    class InfoSerializer(serializers.Serializer):
        class SwitchItemSerializer(serializers.Serializer):
            master = HostInfoSerializer(help_text=_("主库信息"))
            slave = HostInfoSerializer(help_text=_("从库信息"))

        switch_tuples = serializers.ListSerializer(help_text=_("切换的主从组"), child=SwitchItemSerializer())
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))

    infos = serializers.ListField(help_text=_("单据信息"), child=InfoSerializer())
    force = serializers.BooleanField(help_text=_("是否强制执行(互切不强制，故障切强制)"), default=False, required=False)
    is_check_process = serializers.BooleanField(help_text=_("是否检测连接"))
    is_check_delay = serializers.BooleanField(
        help_text=_("是否检测数据同步延时情况(互切单据延时属于强制检测，故必须传True)"), default=True, required=False
    )
    is_verify_checksum = serializers.BooleanField(help_text=_("是否检测历史数据检验结果"))

    def validate(self, attrs):
        if attrs["force"] or not attrs["is_check_delay"]:
            raise serializers.ValidationError(_("主从互切场景：非强制执行，强制检查延时"))

        return attrs


class TendbMasterSlaveSwitchParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.tendb_cluster_remote_switch_scene


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_MASTER_SLAVE_SWITCH)
class TendbMasterSlaveSwitchFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbMasterSlaveSwitchDetailSerializer
    inner_flow_builder = TendbMasterSlaveSwitchParamBuilder
    inner_flow_name = _("TendbCluster 主从互换执行")

    @property
    def need_manual_confirm(self):
        return False

    @property
    def need_itsm(self):
        return False
