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

from backend.ticket import builders
from backend.ticket.builders.mysql.mysql_openarea import MysqlOpenAreaDetailSerializer, MysqlOpenAreaParamBuilder
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder
from backend.ticket.constants import TicketType


class TendbOpenAreaDetailSerializer(MysqlOpenAreaDetailSerializer):
    pass


class TendbOpenAreaParamBuilder(MysqlOpenAreaParamBuilder):
    pass


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_OPEN_AREA)
class TendbOpenAreaFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbOpenAreaDetailSerializer
    inner_flow_builder = TendbOpenAreaParamBuilder
    inner_flow_name = _("Tendb Cluster 开区执行")
