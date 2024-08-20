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

from backend.db_meta.enums import ClusterType
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.mysql.mysql_ha_clear import MySQLHaClearDetailSerializer
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder
from backend.ticket.constants import TicketType


class TendbClearDetailSerializer(MySQLHaClearDetailSerializer):
    def validate(self, attrs):
        """校验库表选择器信息是否正确"""
        super().validate_cluster_can_access(attrs)
        # 库表选择器校验
        super().validate_database_table_selector(attrs)
        # 校验集群类型只能是高可用
        super().validated_cluster_type(attrs, cluster_type=ClusterType.TenDBCluster)
        return attrs


class TendbClearFlowParamBuilder(builders.FlowParamBuilder):
    """TendbCluster清档执行单据参数"""

    controller = SpiderController.truncate_database

    def format_ticket_data(self):
        pass


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_TRUNCATE_DATABASE)
class TendbClearFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbClearDetailSerializer
    inner_flow_builder = TendbClearFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 清档执行")
