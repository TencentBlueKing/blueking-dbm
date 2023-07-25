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
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder
from backend.ticket.constants import TicketType


class RedisAddSlaveDetailSerializer(serializers.Serializer):
    """新建从库"""

    class InfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        pairs = serializers.ListField(help_text=_("主从切换对"), child=serializers.DictField())

    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisAddSlaveParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_cluster_add_slave

    def format_ticket_data(self):
        super().format_ticket_data()


class RedisAddSlaveResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]

        for info_index, info in enumerate(ticket_data["infos"]):
            for pair in info["pairs"]:
                pair["redis_slave"] = info.pop(pair["redis_master"]["ip"], [])

        next_flow.save(update_fields=["details"])
        super().post_callback()


@builders.BuilderFactory.register(TicketType.REDIS_CLUSTER_ADD_SLAVE)
class RedisAddSlaveFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisAddSlaveDetailSerializer
    inner_flow_builder = RedisAddSlaveParamBuilder
    inner_flow_name = _("Redis 新建从库")
    resource_batch_apply_builder = RedisAddSlaveResourceParamBuilder

    @property
    def need_itsm(self):
        return False

    def patch_ticket_detail(self):
        """redis_master -> backend_group"""

        super().patch_ticket_detail()

        for info in self.ticket.details["infos"]:
            info["resource_spec"] = {}
            for pair in info["pairs"]:
                info["resource_spec"][pair["redis_master"]["ip"]] = pair["redis_slave"]

        self.ticket.save(update_fields=["details"])
