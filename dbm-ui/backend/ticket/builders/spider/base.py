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

from backend.configuration.constants import DBType
from backend.ticket.builders import TicketFlowBuilder
from backend.ticket.builders.common.base import MySQLTicketFlowBuilderPatchMixin
from backend.ticket.builders.mysql.base import (
    MySQLBaseOperateDetailSerializer,
    MySQLBaseOperateResourceParamBuilder,
    MySQLClustersTakeDownDetailsSerializer,
)


class BaseTendbTicketFlowBuilder(MySQLTicketFlowBuilderPatchMixin, TicketFlowBuilder):
    group = DBType.Tendb.value


class TendbBaseOperateDetailSerializer(MySQLBaseOperateDetailSerializer):
    pass


class TendbClustersTakeDownDetailsSerializer(MySQLClustersTakeDownDetailsSerializer):
    is_only_delete_slave_domain = serializers.BooleanField(help_text=_("是否只禁用只读集群"), required=False)
    is_only_add_slave_domain = serializers.BooleanField(help_text=_("是否只启用只读集群"), required=False)


class TendbBaseOperateResourceParamBuilder(MySQLBaseOperateResourceParamBuilder):
    pass
