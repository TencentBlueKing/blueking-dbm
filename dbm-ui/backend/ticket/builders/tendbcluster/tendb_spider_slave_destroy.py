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

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.models import ProxyInstance
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.common.base import HostRecycleSerializer
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class SpiderSlaveDestroyDetailSerializer(TendbBaseOperateDetailSerializer):
    is_safe = serializers.BooleanField(help_text=_("是否做安全检测"), required=False, default=True)
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收信息"), default=HostRecycleSerializer.DEFAULT)


class SpiderSlaveDestroyFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.destroy_tendb_slave_cluster


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_SPIDER_SLAVE_DESTROY, is_recycle=True)
class SpiderSlaveApplyFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = SpiderSlaveDestroyDetailSerializer
    inner_flow_builder = SpiderSlaveDestroyFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 只读接入层下架")
    need_patch_recycle_host_details = True

    def get_reduce_spider_slave(self):
        cluster_ids = self.ticket.details["cluster_ids"]
        # 获取所有下架的spider slave
        reduce_spider_slaves = ProxyInstance.objects.select_related("machine").filter(
            cluster__in=cluster_ids, tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE.value
        )
        # 获取下架的机器信息，并补充到details中
        reduce_spider_slave_hosts = [
            {"ip": spider.machine.ip, "bk_host_id": spider.machine.bk_host_id} for spider in reduce_spider_slaves
        ]
        self.ticket.details["old_nodes"] = {"reduce_spider_slave_hosts": reduce_spider_slave_hosts}

    def patch_ticket_detail(self):
        self.get_reduce_spider_slave()
        super().patch_ticket_detail()
