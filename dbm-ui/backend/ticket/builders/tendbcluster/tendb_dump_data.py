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

from backend.ticket import builders
from backend.ticket.builders.mysql.mysql_dump_data import (
    MySQLDumpDataDetailSerializer,
    MySQLDumpDataFlowBuilder,
    MySQLDumpDataFlowParamBuilder,
    MySQLDumpDataItsmFlowParamsBuilder,
)
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class TendbClusterDumpDataDetailSerializer(MySQLDumpDataDetailSerializer, TendbBaseOperateDetailSerializer):
    pass


class TendbClusterDumpDataFlowParamBuilder(MySQLDumpDataFlowParamBuilder):
    pass


class TendbClusterDumpDataItsmFlowParamsBuilder(MySQLDumpDataItsmFlowParamsBuilder):
    pass


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_DUMP_DATA)
class TendbClusterDumpDataFlowBuilder(BaseTendbTicketFlowBuilder, MySQLDumpDataFlowBuilder):
    serializer = TendbClusterDumpDataDetailSerializer
    itsm_flow_builder = TendbClusterDumpDataItsmFlowParamsBuilder
    inner_flow_builder = TendbClusterDumpDataFlowParamBuilder
    inner_flow_name = _("Tendb Cluster 数据导出执行")
