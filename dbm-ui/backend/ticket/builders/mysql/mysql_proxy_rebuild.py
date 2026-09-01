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
from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.flow.engine.controller.mysql import MySQLController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import InstanceInfoSerializer
from backend.ticket.builders.mysql.base import BaseMySQLHATicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class MysqlProxyRebuildDetailSerializer(MySQLBaseOperateDetailSerializer):
    class ProxyInfoSerializer(serializers.Serializer):
        rebuild_proxy_hosts = serializers.ListField(help_text=_("实例信息"), child=InstanceInfoSerializer())
        cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=True)

    infos = serializers.ListField(help_text=_("重建实例列表"), child=ProxyInfoSerializer())
    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"), default=True, required=False)

    def to_representation(self, instance):
        return instance


class MysqlProxyRebuildParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_proxy_rebuild_scene


@builders.BuilderFactory.register(TicketType.MYSQL_PROXY_REBUILD, iam=ActionEnum.MYSQL_MANAGE)
class MysqlProxyRebuildFlowBuilder(BaseMySQLHATicketFlowBuilder):
    serializer = MysqlProxyRebuildDetailSerializer
    inner_flow_builder = MysqlProxyRebuildParamBuilder
    inner_flow_name = _("MySQL Proxy原地重建")
    validator = MySQLController.mysql_proxy_rebuild_scene.validator
