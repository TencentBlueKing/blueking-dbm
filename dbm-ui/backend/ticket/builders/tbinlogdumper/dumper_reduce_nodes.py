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
import functools
import operator
from collections import defaultdict
from typing import Dict, List

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.models import ExtraProcessInstance
from backend.db_services.mysql.dumper.models import DumperSubscribeConfig
from backend.flow.engine.controller.tbinlogdumper import TBinlogDumperController
from backend.ticket import builders
from backend.ticket.builders.common.base import SkipToRepresentationMixin
from backend.ticket.builders.tendbcluster.base import BaseDumperTicketFlowBuilder
from backend.ticket.constants import TicketFlowStatus, TicketType


class TbinlogdumperReduceNodesDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    dumper_instance_ids = serializers.ListField(help_text=_("dumper实例ID"), child=serializers.IntegerField())


class TbinlogdumperReduceNodesFlowParamBuilder(builders.FlowParamBuilder):
    controller = TBinlogDumperController.reduce_nodes_scene

    @classmethod
    def make_dumper_reduce_infos(cls, dumpers):
        cloud_id__dumper_ids: Dict[int, List[int]] = defaultdict(list)
        for dumper in dumpers:
            cloud_id__dumper_ids[dumper.bk_cloud_id].append(dumper.id)

        dumper_destroy_infos = [
            {"bk_cloud_id": cloud_id, "reduce_ids": dumper_ids}
            for cloud_id, dumper_ids in cloud_id__dumper_ids.items()
        ]
        return dumper_destroy_infos

    def format_ticket_data(self):
        dumper_instances = ExtraProcessInstance.objects.filter(id__in=self.ticket_data["dumper_instance_ids"])
        self.ticket_data["infos"] = self.make_dumper_reduce_infos(dumper_instances)

    def post_callback(self):
        if self.ticket.current_flow().status != TicketFlowStatus.SUCCEEDED:
            return

        # 从dumper配置表剔除删除的dumper节点。Optimization: 如果后端mysql采用8.0以上的版本，查询可以用JSON_OVERLAP
        dumper_process_filter = functools.reduce(
            operator.or_, [Q(dumper_process_ids__contains=id) for id in self.ticket_data["dumper_process_ids"]]
        )
        dumper_configs = DumperSubscribeConfig.objects.filter(dumper_process_filter)
        for dumper_config in dumper_configs:
            diff = set(dumper_config.dumper_process_ids) - set(self.ticket_data["dumper_process_ids"])
            dumper_config.dumper_process_ids = list(diff)

        DumperSubscribeConfig.objects.bulk_update(dumper_configs, fields=["dumper_process_ids"])


@builders.BuilderFactory.register(TicketType.TBINLOGDUMPER_REDUCE_NODES)
class TbinlogdumperReduceNodesFlowBuilder(BaseDumperTicketFlowBuilder):
    serializer = TbinlogdumperReduceNodesDetailSerializer
    inner_flow_builder = TbinlogdumperReduceNodesFlowParamBuilder
    inner_flow_name = _("Tbinlogdumper 下架")
