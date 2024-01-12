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

from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import Cluster
from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.ticket import builders
from backend.ticket.builders.sqlserver.base import BaseSQLServerTicketFlowBuilder, SQLServerTakeDownDetailsSerializer
from backend.ticket.constants import FlowRetryType, TicketType


class SQLServerDestroyDetailSerializer(SQLServerTakeDownDetailsSerializer):
    pass


class SQLServerDestroyFlowParamBuilder(builders.FlowParamBuilder):
    single_controller = SqlserverController.fake_scene
    ha_controller = SqlserverController.fake_scene

    def build_controller_info(self) -> dict:
        # 根据集群类型判断应该取哪个controller
        cluster = Cluster.objects.get(id=self.ticket_data["cluster_ids"][0])
        if cluster.cluster_type == ClusterType.SqlserverHA:
            self.controller = self.ha_controller
        else:
            self.controller = self.single_controller
        return super().build_controller_info()


@builders.BuilderFactory.register(TicketType.SQLSERVER_DESTROY, phase=ClusterPhase.DESTROY)
class SQLServerDestroyFlowBuilder(BaseSQLServerTicketFlowBuilder):
    """Sqlserver下架流程的构建基类"""

    serializer = SQLServerDestroyDetailSerializer
    inner_flow_builder = SQLServerDestroyFlowParamBuilder
    inner_flow_name = _("SQLServer 销毁执行")
    retry_type = FlowRetryType.MANUAL_RETRY
