# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is
distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.ticket import builders
from backend.ticket.builders.sqlserver.sqlserver_rollback_base import (
    SQLServerDBConstructRollbackFlowParamBuilder,
    SQLServerRollbackBaseDetailSerializer,
    SQLServerRollbackCommonFlowBuilder,
)
from backend.ticket.constants import TicketType


class SQLServerRollbackDetailSerializer(SQLServerRollbackBaseDetailSerializer):
    is_time_fixed = serializers.BooleanField(help_text=_("是否指定回档时间"))


@builders.BuilderFactory.register(TicketType.SQLSERVER_ROLLBACK)
class SQLServerDBConstructFlowBuilder(SQLServerRollbackCommonFlowBuilder):
    serializer = SQLServerRollbackDetailSerializer
    # rollback 内部流程走定点构造场景：db_construct_scene
    rollback_flow_param_builder = SQLServerDBConstructRollbackFlowParamBuilder
    inner_flow_builder = SQLServerDBConstructRollbackFlowParamBuilder
    validator = SqlserverController.db_construct_scene.validator
