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

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, Machine
from backend.db_monitor.serializers import AlarmCallBackDataSerializer
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import SkipToRepresentationMixin
from backend.ticket.builders.redis.redis_toolbox_cut_off import (
    RedisClusterCutOffFlowBuilder,
    RedisClusterCutOffResourceParamBuilder,
)
from backend.ticket.constants import TicketType


class RedisClusterAutofixDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    """故障自愈"""

    class InfoSerializer(serializers.Serializer):
        class HostInfoSerializer(serializers.Serializer):
            ip = serializers.IPAddressField()
            spec_id = serializers.IntegerField()

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        proxy = serializers.ListField(help_text=_("proxy列表"), child=HostInfoSerializer(), required=False)
        redis_slave = serializers.ListField(help_text=_("slave列表"), child=HostInfoSerializer(), required=False)

    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL.value
    )
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisClusterAutofixAlarmTransformSerializer(AlarmCallBackDataSerializer):
    # TODO： 这里举个例子，具体逻辑和场景，需各组件 DBA 实现
    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        dimensions = data["callback_message"]["event"]["dimensions"]
        cluster = Cluster.objects.get(immute_domain=dimensions["cluster_domain"])
        machine = Machine.objects.get(bk_host_id=dimensions["bk_host_id"])
        proxy = redis_slave = []
        host_info = [{"ip": machine.ip, "spec_id": machine.spec_id}]
        if dimensions["instance_role"] == InstanceRole.REDIS_PROXY:
            proxy = host_info
        else:
            redis_slave = host_info

        ticket_detail = {
            "infos": [
                {
                    "cluster_id": cluster.id,
                    "bk_cloud_id": cluster.bk_cloud_id,
                    "proxy": proxy,
                    "redis_slave": redis_slave,
                }
            ]
        }
        return ticket_detail


class RedisClusterAutofixParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_auotfix_scene

    def format_ticket_data(self):
        super().format_ticket_data()


class RedisClusterAutofixResourceParamBuilder(RedisClusterCutOffResourceParamBuilder):
    def post_callback(self):
        # 与整机替换的处理方法一致，直接调用父类即可
        super().post_callback()


@builders.BuilderFactory.register(TicketType.REDIS_CLUSTER_AUTOFIX, is_apply=True)
class RedisClusterAutofixFlowBuilder(RedisClusterCutOffFlowBuilder):
    serializer = RedisClusterAutofixDetailSerializer
    alarm_transform_serializer = RedisClusterAutofixAlarmTransformSerializer
    inner_flow_builder = RedisClusterAutofixParamBuilder
    inner_flow_name = _("故障自愈")
    resource_batch_apply_builder = RedisClusterAutofixResourceParamBuilder
    default_need_itsm = True
    default_need_manual_confirm = False

    @property
    def need_itsm(self):
        return True

    def patch_ticket_detail(self):
        # 与整机替换的处理方法一致，直接调用父类即可
        super().patch_ticket_detail()
