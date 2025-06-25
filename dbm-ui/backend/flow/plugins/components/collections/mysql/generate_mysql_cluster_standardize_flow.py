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
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import ALLDEPARTS
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


class GenerateMySQLClusterStandardizeFlowService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data")
        kwargs = data.get_one_of_inputs("kwargs")

        getattr(self, kwargs.get("trans_func"))(global_data, kwargs)
        return True

    @staticmethod
    def generate_from_immute_domains(global_data, kwargs):
        immute_domains = kwargs.get("immute_domains")
        cluster_objects = Cluster.objects.filter(immute_domain__in=immute_domains)
        cluster_ids = list(cluster_objects.values_list("id", flat=True))
        kwargs["cluster_ids"] = cluster_ids

        return GenerateMySQLClusterStandardizeFlowService.generate_from_cluster_ids(global_data, kwargs)

    @staticmethod
    def generate_from_cluster_ids(global_data, kwargs):
        cluster_ids = kwargs.get("cluster_ids")

        ticket_remark = ""
        if "uid" in global_data:
            ticket = Ticket.objects.get(id=global_data["uid"])
            ticket_remark = _("集群标准化, 关联单据: {}".format(ticket.url))

        bk_biz_id = global_data["bk_biz_id"]

        standardize_ticket = Ticket.create_ticket(
            ticket_type=TicketType.MYSQL_CLUSTER_STANDARDIZE,
            creator=global_data["created_by"],
            bk_biz_id=bk_biz_id,
            remark=ticket_remark,
            details={
                "bk_biz_id": bk_biz_id,
                "cluster_type": kwargs.get("cluster_type"),
                "cluster_ids": cluster_ids,
                "departs": kwargs.get("departs", ALLDEPARTS),
                "with_deploy_binary": kwargs.get("with_deploy_binary", True),
                "with_push_config": kwargs.get("with_push_config", True),
                "with_collect_sysinfo": kwargs.get("with_collect_sysinfo", True),
                "with_bk_plugin": kwargs.get("with_bk_plugin", True),
                "with_cc_standardize": kwargs.get("with_cc_standardize", True),
                "with_instance_standardize": kwargs.get("with_instance_standardize", True),
            },
        )

        if "uid" in global_data:
            ticket = Ticket.objects.get(id=global_data["uid"])
            ticket.add_related_ticket(standardize_ticket, desc=_("MySQL 集群标准化"))


class GenerateMySQLClusterStandardizeFlowComponent(Component):
    name = __name__
    code = "generate_mysql_cluster_standardize_flow"
    bound_service = GenerateMySQLClusterStandardizeFlowService
