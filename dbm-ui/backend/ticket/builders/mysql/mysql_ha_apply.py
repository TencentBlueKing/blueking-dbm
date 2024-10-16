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
from typing import Dict, List

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import MASTER_DOMAIN_INITIAL_VALUE, SLAVE_DOMAIN_INITIAL_VALUE, AffinityEnum
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache, DBModule
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.mysql.constants import DEFAULT_ORIGIN_PROXY_PORT, SERVER_PORT_LIMIT_MAX, SERVER_PORT_LIMIT_MIN
from backend.flow.engine.controller.mysql import MySQLController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket.builders import BuilderFactory
from backend.ticket.builders.mysql.base import BaseMySQLHATicketFlowBuilder
from backend.ticket.builders.mysql.mysql_single_apply import (
    MysqlSingleApplyDetailSerializer,
    MysqlSingleApplyFlowBuilder,
    MysqlSingleApplyFlowParamBuilder,
    MysqlSingleApplyResourceParamBuilder,
)
from backend.ticket.constants import TicketType


class MysqlHAApplyDetailSerializer(MysqlSingleApplyDetailSerializer):
    disaster_tolerance_level = serializers.ChoiceField(
        help_text=_("容灾级别"), choices=AffinityEnum.get_choices(), required=False, default=AffinityEnum.NONE.value
    )
    start_proxy_port = serializers.IntegerField(
        help_text=_("Proxy起始端口"),
        required=False,
        min_value=SERVER_PORT_LIMIT_MIN,
        max_value=SERVER_PORT_LIMIT_MAX,
        default=DEFAULT_ORIGIN_PROXY_PORT,
    )

    def validate(self, attrs):
        super().validate(attrs)

        # 验证输入的机器数量是否预期
        if attrs["ip_source"] == IpSource.RESOURCE_POOL:
            return attrs

        backend_machines = attrs["nodes"]["backend"]
        proxy_machines = attrs["nodes"]["proxy"]
        expected_machine_num = 2 * (
            attrs["cluster_count"] // attrs["inst_num"] + bool(attrs["cluster_count"] % attrs["inst_num"])
        )
        if len(proxy_machines) != len(backend_machines) or len(proxy_machines) != expected_machine_num:
            raise serializers.ValidationError(
                _("机器输入数量有误，期待输入{}台proxy和backend机器，但实际输入{}台proxy机器和{}台backend机器").format(
                    expected_machine_num, len(proxy_machines), len(backend_machines)
                )
            )

        return attrs

    def _format_domains(self, domains, instance):
        db_module_name = self.get_db_module_name(instance)
        bk_biz_id = self.context["ticket_ctx"].db_module_id__biz_id_map.get(instance["db_module_id"])
        db_app_abbr = self.context["ticket_ctx"].app_abbr_map.get(bk_biz_id, f"biz-{bk_biz_id}")
        for index, domain in enumerate(domains):
            domains[index]["master"] = MASTER_DOMAIN_INITIAL_VALUE.format(
                db_module_name=db_module_name, db_app_abbr=db_app_abbr, cluster_name=domain["key"]
            )
            domains[index]["slave"] = SLAVE_DOMAIN_INITIAL_VALUE.format(
                db_module_name=db_module_name, db_app_abbr=db_app_abbr, cluster_name=domain["key"]
            )
        return domains


class MysqlHAApplyFlowParamBuilder(MysqlSingleApplyFlowParamBuilder):
    controller = MySQLController.mysql_ha_apply_scene

    def format_cluster_domains(self) -> List[Dict[str, str]]:
        db_module_name = DBModule.objects.get(db_module_id=self.ticket_data["db_module_id"]).db_module_name
        db_app_abbr = AppCache.get_app_attr(self.ticket_data["bk_biz_id"])
        return [
            {
                "name": domain["key"],
                "master": MASTER_DOMAIN_INITIAL_VALUE.format(
                    db_module_name=db_module_name, db_app_abbr=db_app_abbr, cluster_name=domain["key"]
                ).replace("_", "-"),
                "slave": SLAVE_DOMAIN_INITIAL_VALUE.format(
                    db_module_name=db_module_name, db_app_abbr=db_app_abbr, cluster_name=domain["key"]
                ).replace("_", "-"),
            }
            for domain in self.ticket_data["domains"]
        ]

    @classmethod
    def insert_ip_into_apply_infos(cls, ticket_data, apply_infos: List[Dict]):
        backend_nodes = ticket_data["nodes"]["backend"]
        proxy_nodes = ticket_data["nodes"]["proxy"]
        for index, apply_info in enumerate(apply_infos):
            # 每组集群需要两个后端 IP 和两个 Proxy IP
            start, end = index * 2, (index + 1) * 2
            apply_info["mysql_ip_list"] = backend_nodes[start:end]
            apply_info["proxy_ip_list"] = proxy_nodes[start:end]


class MysqlHaApplyResourceParamBuilder(MysqlSingleApplyResourceParamBuilder):
    def format(self):
        # 在跨机房亲和性要求下，接入层proxy的亲和性要求至少分布在2个机房
        self.ticket_data["resource_spec"]["proxy"]["group_count"] = 2

    @classmethod
    def insert_ip_into_apply_infos(cls, ticket_data, apply_infos: List[Dict]):
        backend_nodes = [[group["master"], group["slave"]] for group in ticket_data["nodes"]["backend_group"]]
        ticket_data["nodes"]["backend"] = list(itertools.chain(*backend_nodes))
        MysqlHAApplyFlowParamBuilder.insert_ip_into_apply_infos(ticket_data, apply_infos)

    def post_callback(self):
        next_flow = self.ticket.next_flow()

        # 组装后台部署节点格式
        apply_infos = next_flow.details["ticket_data"]["apply_infos"]
        self.insert_ip_into_apply_infos(next_flow.details["ticket_data"], apply_infos)
        # 补充规格信息
        resource_spec = next_flow.details["ticket_data"]["resource_spec"]
        resource_spec["backend"] = resource_spec.pop("master")

        next_flow.details["ticket_data"].update(apply_infos=apply_infos)
        next_flow.save(update_fields=["details"])


@BuilderFactory.register(
    TicketType.MYSQL_HA_APPLY, is_apply=True, cluster_type=ClusterType.TenDBHA, iam=ActionEnum.MYSQL_APPLY
)
class MysqlHAApplyFlowBuilder(BaseMySQLHATicketFlowBuilder, MysqlSingleApplyFlowBuilder):
    serializer = MysqlHAApplyDetailSerializer
    inner_flow_builder = MysqlHAApplyFlowParamBuilder
    inner_flow_name = _("MySQL高可用部署执行")
    resource_apply_builder = MysqlHaApplyResourceParamBuilder

    def patch_ticket_detail(self):
        super().patch_dbconfig(cluster_type=ClusterType.TenDBHA)
        super().patch_ticket_detail()
