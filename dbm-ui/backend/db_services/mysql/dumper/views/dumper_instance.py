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
import itertools
from collections import defaultdict
from typing import Dict, List

from django.utils.translation import ugettext as _

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.enums.extra_process_type import ExtraProcessType
from backend.db_meta.models import Cluster
from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.db_services.mysql.dumper.filters import DumperInstanceListFilter
from backend.db_services.mysql.dumper.serializers import DumperInstanceConfigSerializer
from backend.ticket.constants import TicketStatus, TicketType
from backend.ticket.models import Ticket

SWAGGER_TAG = "dumper"


class DumperInstanceViewSet(viewsets.AuditedModelViewSet):
    pagination_class = AuditedLimitOffsetPagination
    queryset = ExtraProcessInstance.objects.filter(proc_type=ExtraProcessType.TBINLOGDUMPER)
    serializer_class = DumperInstanceConfigSerializer
    filter_class = DumperInstanceListFilter

    def get_queryset(self):
        return self.queryset.filter(bk_biz_id=self.kwargs["bk_biz_id"])

    @common_swagger_auto_schema(
        operation_summary=_("查询数据订阅实例列表"),
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        dumper_results = resp.data["results"]

        # 查询集群相关信息
        cluster_ids = [data["cluster_id"] for data in resp.data["results"]]
        id__cluster = {
            cluster.id: cluster
            for cluster in Cluster.objects.prefetch_related("storageinstance_set").filter(id__in=cluster_ids)
        }

        # 补充订阅实例的信息
        for data in dumper_results:
            extra_config = data.pop("extra_config")
            # dumper是否已经不在集群master主机上 ---> 需要迁移
            source_cluster = id__cluster[data["cluster_id"]]
            master = source_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
            data["need_transfer"] = data["ip"] != master.machine.ip
            # 补充集群信息和集群的master信息
            data["source_cluster"] = source_cluster.simple_desc
            data["source_cluster"]["master_ip"] = master.machine.ip
            data["source_cluster"]["master_port"] = master.port
            # 补充订阅配置信息
            dumper_config_fields = ["dumper_id", "protocol_type", "target_address", "target_port", "add_type"]
            for field in dumper_config_fields:
                data[field] = extra_config.get(field)

        # 查询dumper实例的状态, 因为dumper实例没有record表，因此直接查询正在运行的相关单据
        dumper_ticket_types = TicketType.get_ticket_type_by_db("tbinlogdumper")
        dumper_ticket_types.remove(TicketType.TBINLOGDUMPER_INSTALL)
        active_tickets = Ticket.objects.filter(
            bk_biz_id=kwargs["bk_biz_id"], status=TicketStatus.RUNNING, ticket_type__in=dumper_ticket_types
        )
        # 获取每个dumper单据状态与id的映射
        dumper_inst_id__ticket: Dict[int, str] = {}
        for ticket_type in dumper_ticket_types:
            ticket_infos = active_tickets.filter(ticket_type=ticket_type).values_list(
                "details__dumper_instance_ids", "id"
            )
            for info in ticket_infos:
                dumper_inst_id__ticket.update({d: (ticket_type, info[1]) for d in info[0]})

        # 对每个dumper实例填充正在运行的状态，一个dumper只会处于一种变更状态
        for data in dumper_results:
            if data["id"] not in dumper_inst_id__ticket:
                data["operation"] = {}
            else:
                data["operation"] = {
                    "ticket_type": dumper_inst_id__ticket[data["id"]][0],
                    "ticket_id": dumper_inst_id__ticket[data["id"]][1],
                }

        return resp
