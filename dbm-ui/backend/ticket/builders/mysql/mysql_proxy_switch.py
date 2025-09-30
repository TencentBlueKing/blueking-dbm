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
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import (
    BaseOperateResourceParamBuilder,
    DisplayInfoSerializer,
    HostRecycleSerializer,
    InstanceInfoSerializer,
)
from backend.ticket.builders.common.constants import OperaObjType
from backend.ticket.builders.mysql.base import (
    BaseMySQLHATicketFlowBuilder,
    MySQLBaseOperateDetailSerializer,
    MySQLBasePauseParamBuilder,
)
from backend.ticket.constants import FlowRetryType, TicketType


class MysqlProxySwitchDetailSerializer(MySQLBaseOperateDetailSerializer):
    class SwitchInfoSerializer(DisplayInfoSerializer):
        class OldProxySerializer(serializers.Serializer):
            proxy = serializers.ListSerializer(child=InstanceInfoSerializer())

        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
        old_nodes = OldProxySerializer(help_text=_("旧Proxy实例信息"))
        resource_spec = serializers.JSONField(help_text=_("资源规格"))
        related_instances = serializers.ListSerializer(
            help_text=_("关联的实例"), child=serializers.JSONField(), required=False
        )

    ip_source = serializers.ChoiceField(
        help_text=_("机器来源"), choices=IpSource.get_choices(), required=False, default=IpSource.RESOURCE_POOL
    )
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收信息"), default=HostRecycleSerializer.DEFAULT)
    is_safe = serializers.BooleanField(help_text=_("是否安全模式"), required=False, default=True)
    infos = serializers.ListField(help_text=_("替换信息"), child=SwitchInfoSerializer())
    opera_object = serializers.ChoiceField(help_text=_("操作对象类型"), choices=OperaObjType.get_choices(), required=False)
    disable_manual_confirm = serializers.BooleanField(help_text=(_("自愈单据禁用人工确认")), default=False)


class MysqlProxySwitchParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_proxy_switch_scene
    validator = None


class MysqlProxySwitchResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        self.patch_info_common_affinity(
            role="target_proxys", remain_machine_type=MachineType.PROXY, replace_key="proxy", tolerance=0.5
        )


@builders.BuilderFactory.register(TicketType.MYSQL_PROXY_SWITCH, is_apply=True, is_recycle=True)
class MysqlProxySwitchFlowBuilder(BaseMySQLHATicketFlowBuilder):
    need_patch_recycle_host_details = True
    need_patch_machine_details = True
    retry_type = FlowRetryType.MANUAL_RETRY
    serializer = MysqlProxySwitchDetailSerializer
    inner_flow_builder = MysqlProxySwitchParamBuilder
    resource_batch_apply_builder = MysqlProxySwitchResourceParamBuilder
    pause_node_builder = MySQLBasePauseParamBuilder
