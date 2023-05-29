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

from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.ticket import builders
from backend.ticket.builders import TicketFlowBuilder
from backend.ticket.builders.common.base import (
    BaseOperateResourceParamBuilder,
    SkipToRepresentationMixin,
    SQLServerTicketFlowBuilderPatchMixin,
)
from backend.ticket.builders.mysql.base import MySQLClustersTakeDownDetailsSerializer


class BaseSQLServerTicketFlowBuilder(SQLServerTicketFlowBuilderPatchMixin, TicketFlowBuilder):
    group = DBType.Sqlserver.value


class SQLServerBasePauseParamBuilder(builders.PauseParamBuilder):
    pass


class SQLServerTakeDownDetailsSerializer(MySQLClustersTakeDownDetailsSerializer):
    """sqlserver的下架逻辑同mysql"""

    pass


class SQLServerBaseOperateDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    """
    sqlserver操作的基类，主要功能:
    1. 屏蔽序列化的to_representation
    2. 存放sqlserver操作的各种校验逻辑
    """

    def validate(self, attrs):
        # 默认全局校验只需要校验集群的状态
        return attrs


class SQLServerBaseOperateResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        super().format()

    def post_callback(self):
        super().post_callback()
