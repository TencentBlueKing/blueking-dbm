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
    SQLServerDBRollbackInLocalFlowParamBuilder,
    SQLServerRollbackBaseDetailSerializer,
    SQLServerRollbackCommonFlowBuilder,
)
from backend.ticket.constants import TicketType


class SQLServerLocalDetailSerializer(SQLServerRollbackBaseDetailSerializer):
    """本地构造(原地回档)：源集群与目标集群为同一集群，无需传目标集群ID"""

    class LocalRollbackInfoSerializer(SQLServerRollbackBaseDetailSerializer.RollbackInfoSerializer):
        # 原地回档不传目标集群，目标集群与源集群保持一致
        dst_cluster = serializers.IntegerField(help_text=_("目标集群ID"), required=False)

        def validate(self, attrs):
            # 原地回档：目标集群ID等于源集群ID
            attrs["dst_cluster"] = attrs["src_cluster"]
            return attrs

    infos = serializers.ListSerializer(help_text=_("迁移信息列表"), child=LocalRollbackInfoSerializer())
    is_time_fixed = serializers.BooleanField(help_text=_("是否指定回档时间"))


@builders.BuilderFactory.register(TicketType.SQLSERVER_ROLLBACK_LOCAL)
class SQLServerRollbackLocalFlowBuilder(SQLServerRollbackCommonFlowBuilder):
    serializer = SQLServerLocalDetailSerializer
    # rollback 内部流程走本地(原地)构造场景：db_rollback_in_local_scene
    rollback_flow_param_builder = SQLServerDBRollbackInLocalFlowParamBuilder
    inner_flow_builder = SQLServerDBRollbackInLocalFlowParamBuilder
    rollback_flow_alias = _("SQLServer 原地回档执行")
    validator = SqlserverController.db_rollback_in_local_scene.validator
