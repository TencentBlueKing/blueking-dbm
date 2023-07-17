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

from backend.flow.consts import MySQLBackupFileTagEnum, MySQLBackupTypeEnum, TenDBBackUpLocation
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class TendbFullBackUpDetailSerializer(TendbBaseOperateDetailSerializer):
    class FullBackUpItemSerializer(serializers.Serializer):
        class FullBackUpClusterItemSerializer(serializers.Serializer):
            id = serializers.IntegerField(help_text=_("集群ID"))
            backup_local = serializers.ChoiceField(help_text=_("备份位置"), choices=TenDBBackUpLocation.get_choices())
            spider_mnt_address = serializers.CharField(help_text=_("spider临时节点地址(备份位置是spider_mnt才需要)"), required=False)

        backup_type = serializers.ChoiceField(help_text=_("备份选项"), choices=MySQLBackupTypeEnum.get_choices())
        file_tag = serializers.ChoiceField(help_text=_("备份保存时间"), choices=MySQLBackupFileTagEnum.get_choices())
        clusters = serializers.ListSerializer(help_text=_("集群备份信息"), child=FullBackUpClusterItemSerializer())

    infos = FullBackUpItemSerializer()

    def validate(self, attrs):
        for cluster in attrs["infos"]["clusters"]:
            if cluster["backup_local"] == TenDBBackUpLocation.SPIDER_MNT and "spider_mnt_address" not in cluster:
                raise serializers.ValidationError(_("备份位置选择spider_mnt时，请提供临时节点的地址"))

        return attrs


class TendbFullBackUpFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.full_backup

    def format_ticket_data(self):
        pass


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_FULL_BACKUP)
class TendbFullBackUpFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbFullBackUpDetailSerializer
    inner_flow_builder = TendbFullBackUpFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 全库备份")

    @property
    def need_itsm(self):
        return False
