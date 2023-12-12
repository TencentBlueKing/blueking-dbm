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

from collections import defaultdict
from typing import Dict, List

from django.utils.translation import ugettext_lazy as _

from backend.db_meta.enums import ClusterPhase
from backend.db_meta.enums.extra_process_type import ExtraProcessType
from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.flow.engine.controller.mysql import MySQLController
from backend.flow.engine.controller.tbinlogdumper import TBinlogDumperController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLClustersTakeDownDetailsSerializer
from backend.ticket.builders.tbinlogdumper.dumper_reduce_nodes import TbinlogdumperReduceNodesFlowParamBuilder
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.models import Flow


class MysqlHADestroyDetailSerializer(MySQLClustersTakeDownDetailsSerializer):
    pass


class MysqlHADestroyFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_ha_destroy_scene


class MysqlDumperDestroyParamBuilder(builders.FlowParamBuilder):
    controller = TBinlogDumperController.reduce_nodes_scene

    def format_ticket_data(self):
        self.ticket_data["ticket_type"] = TicketType.TBINLOGDUMPER_REDUCE_NODES
        self.ticket_data["infos"] = self.ticket_data.pop("dumper_destroy_infos")


@builders.BuilderFactory.register(TicketType.MYSQL_HA_DESTROY, phase=ClusterPhase.DESTROY)
class MysqlHaDestroyFlowBuilder(BaseMySQLTicketFlowBuilder):
    """Mysql下架流程的构建基类"""

    serializer = MysqlHADestroyDetailSerializer
    inner_flow_builder = MysqlHADestroyFlowParamBuilder
    inner_flow_name = _("MySQL高可用销毁执行")
    dumper_flow_builder = MysqlDumperDestroyParamBuilder
    retry_type = FlowRetryType.MANUAL_RETRY

    def cluster_dumper_destroy(self):
        cluster_ids = self.ticket.details["cluster_ids"]
        dumper_instances = ExtraProcessInstance.objects.filter(
            cluster_id__in=cluster_ids, proc_type=ExtraProcessType.TBINLOGDUMPER
        )
        return TbinlogdumperReduceNodesFlowParamBuilder.make_dumper_reduce_infos(dumper_instances)

    def patch_ticket_detail(self):
        # TODO: 集群下架流程，暂时不需要联动dumper下架，后续看体验再加上
        # self.ticket.update_details(dumper_destroy_infos=self.cluster_dumper_destroy())
        pass

    def custom_ticket_flows(self):
        # 下架流程
        flows = [
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=self.inner_flow_builder(self.ticket).get_params(),
                flow_alias=self.inner_flow_name,
                retry_type=self.retry_type,
            )
        ]
        # 如果存在dumper，则串dumper下架流程
        if self.ticket.details.get("dumper_destroy_infos"):
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.INNER_FLOW.value,
                    details=self.dumper_flow_builder(self.ticket).get_params(),
                    flow_alias=_("dumper 下架"),
                    retry_type=self.retry_type,
                )
            )

        return flows
