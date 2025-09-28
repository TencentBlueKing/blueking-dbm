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

from backend.db_meta.enums import MachineType
from backend.db_services.dbbase.constants import IpSource, SourceType
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder
from backend.ticket.builders.mysql.base import BaseMySQLHATicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class MysqlProxyAddDetailSerializer(MySQLBaseOperateDetailSerializer):
    class AddInfoSerializer(serializers.Serializer):
        resource_spec = serializers.JSONField(help_text=_("资源规格"), required=False)
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
        current_proxy_num = serializers.IntegerField(help_text=_("当前proxy数量"), required=False)

    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), required=False, default=IpSource.MANUAL_INPUT
    )
    source_type = serializers.ChoiceField(
        help_text=_("资源来源类型"), choices=SourceType.get_choices(), required=False, default=SourceType.RESOURCE_AUTO
    )
    infos = serializers.ListField(help_text=_("添加信息"), child=AddInfoSerializer())


class MysqlProxyAddParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_proxy_add_scene
    validator = MySQLController.mysql_proxy_add_scene.validator


class MysqlProxyAddResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        self.patch_info_common_affinity(role="new_proxys", remain_machine_type=MachineType.PROXY, tolerance=0.5)


@builders.BuilderFactory.register(TicketType.MYSQL_PROXY_ADD, is_apply=True)
class MysqlProxyAddFlowBuilder(BaseMySQLHATicketFlowBuilder):
    serializer = MysqlProxyAddDetailSerializer
    inner_flow_builder = MysqlProxyAddParamBuilder
    resource_batch_apply_builder = MysqlProxyAddResourceParamBuilder
