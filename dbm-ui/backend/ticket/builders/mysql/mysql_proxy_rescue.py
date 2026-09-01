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

from backend.db_meta.enums import MachineType
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.mysql import MySQLController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import BaseOperateResourceParamBuilder, InstanceInfoSerializer
from backend.ticket.builders.mysql.base import BaseMySQLHATicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class MysqlProxyRescueDetailSerializer(MySQLBaseOperateDetailSerializer):
    class ClusterInfoSerializer(serializers.Serializer):
        class OldProxySerializer(serializers.Serializer):
            proxy = serializers.ListSerializer(child=InstanceInfoSerializer())

        old_nodes = OldProxySerializer(help_text=_("旧Proxy实例信息"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"))
        cluster_id = serializers.IntegerField(help_text=_("集群 ID"))
        auto_cleanup_old_proxies = serializers.BooleanField(help_text=_("是否自动清理旧 Proxy"))

    infos = serializers.ListField(help_text=_("重建 Proxy 集群列表"), child=ClusterInfoSerializer())
    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL.value
    )


class MysqlProxyRescueParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_proxy_rescue_scene


class MysqlProxySwitchResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        self.patch_info_common_affinity(
            role="new_proxies", remain_machine_type=MachineType.PROXY, replace_key="proxy", tolerance=0.5
        )


@builders.BuilderFactory.register(TicketType.MYSQL_PROXY_RESCUE, iam=ActionEnum.MYSQL_MANAGE)
class MysqlProxyRescueFlowBuilder(BaseMySQLHATicketFlowBuilder):
    serializer = MysqlProxyRescueDetailSerializer
    inner_flow_builder = MysqlProxyRescueParamBuilder
    inner_flow_name = _("MySQL Proxy灾难重建")
    resource_batch_apply_builder = MysqlProxySwitchResourceParamBuilder
    # validator = MySQLController.mysql_proxy_rescue_scene.validator
