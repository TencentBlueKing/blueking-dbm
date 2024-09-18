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
from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder
from backend.ticket.constants import FlowRetryType, TicketType


class QueryPkgListByCompareVersionSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField()
    higher_major_version = serializers.BooleanField(default=False)

    class Meta:
        swagger_schema_fields = {"cluster_id": 123, "higher_major_version": False}


class TendbhaTransferToOtherBizSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("源业务ID"))
    target_biz_id = serializers.IntegerField(help_text=_("目标业务ID"))
    cluster_domain_list = serializers.ListField(child=serializers.CharField())
    db_module_id = serializers.IntegerField()
    need_clone_priv_rules = serializers.BooleanField(default=False)

    class Meta:
        swagger_schema_fields = {
            "bk_biz_id": 11,
            "target_biz_id": 123,
            "cluster_domain_list": [],
            "db_module_id": 123,
            "need_clone_priv_rules": False,
        }


class TendbhaTransferToOtherBizFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.tranfer_biz_scene


@builders.BuilderFactory.register(TicketType.MYSQL_HA_TRANSFER_TO_OTHER_BIZ)
class TendbhaTransferToOtherBizFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbhaTransferToOtherBizSerializer
    inner_flow_builder = TendbhaTransferToOtherBizFlowParamBuilder
    inner_flow_name = _("TenDBHa集群迁移到其他业务")
    retry_type = FlowRetryType.MANUAL_RETRY


class TendbhaAddSlaveDomainSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群id"))
    slave_ip = serializers.CharField(help_text=_("slave ip"))
    slave_port = serializers.IntegerField(help_text=_("slave port"))
    domain_name = serializers.CharField(help_text=_("slave domain"))

    class Meta:
        swagger_schema_fields = {
            "bk_biz_id": 11,
            "slave_ip": "1.1.1.1",
            "slave_port": 3306,
            "domain_name": "",
        }
