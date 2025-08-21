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
from backend.ticket.builders.common.base import DisplayInfoSerializer, HostInfoSerializer
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class MysqlProxyReduceDetailSerializer(MySQLBaseOperateDetailSerializer):
    class ProxyInfoSerializer(DisplayInfoSerializer):
        class OldProxySerializer(serializers.Serializer):
            origin_proxy = serializers.ListSerializer(help_text=_("proxy"), child=HostInfoSerializer())

        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
        row_key = serializers.CharField(help_text=_("唯一值"), required=False)
        origin_proxy_ip = HostInfoSerializer(help_text=_("缩容主机信息"))
        old_nodes = OldProxySerializer(help_text=_("缩容指定主机"), required=False)

    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"))
    infos = serializers.ListField(help_text=_("替换信息"), child=ProxyInfoSerializer())


class MysqlProxyReduceFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_proxy_reduce_scene
    # 暂时先为空，等校验函数出来再替换
    validator = MySQLController.mysql_proxy_reduce_scene.validator


@builders.BuilderFactory.register(TicketType.MYSQL_PROXY_REDUCE, is_recycle=True)
class MysqlProxyReduceFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MysqlProxyReduceDetailSerializer
    inner_flow_builder = MysqlProxyReduceFlowParamBuilder
    inner_flow_name = _("Mysql proxy 缩容")
    need_patch_recycle_host_details = True
    need_patch_machine_details = True

    def patch_ticket_detail(self):
        super().patch_ticket_detail()
