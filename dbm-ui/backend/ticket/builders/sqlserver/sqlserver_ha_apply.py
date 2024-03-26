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
from typing import Dict, List

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import MASTER_DOMAIN_INITIAL_VALUE, SLAVE_DOMAIN_INITIAL_VALUE, AffinityEnum
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import DBModule
from backend.db_services.cmdb.biz import get_db_app_abbr
from backend.db_services.dbbase.constants import IpSource
from backend.flow.consts import DEFAULT_SQLSERVER_PORT
from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket.builders import BuilderFactory
from backend.ticket.builders.sqlserver.sqlserver_single_apply import (
    SQLServerSingleApplyDetailSerializer,
    SQLServerSingleApplyFlowBuilder,
    SQLServerSingleApplyFlowParamBuilder,
    SQLServerSingleApplyResourceParamBuilder,
)
from backend.ticket.constants import TicketType


class SQLServerHAApplyDetailSerializer(SQLServerSingleApplyDetailSerializer):
    disaster_tolerance_level = serializers.ChoiceField(
        help_text=_("容灾级别"), choices=AffinityEnum.get_choices(), required=False, default=AffinityEnum.NONE.value
    )
    start_mssql_port = serializers.IntegerField(
        help_text=_("SQLServer起始端口"), required=False, default=DEFAULT_SQLSERVER_PORT
    )

    def validate(self, attrs):
        super().validate(attrs)

        # 验证输入的机器数量是否预期
        expected_count = 2 * (
            attrs["cluster_count"] // attrs["inst_num"] + bool(attrs["cluster_count"] % attrs["inst_num"])
        )
        if attrs["ip_source"] == IpSource.RESOURCE_POOL:
            machine_count = attrs["resource_spec"]["backend"]["count"]
        else:
            machine_count = len(attrs["nodes"]["backend"])
        if machine_count != expected_count:
            raise serializers.ValidationError(_("机器输入数量{}有误，预期数量{}").format(expected_count, machine_count))

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


class SQLServerHAApplyFlowParamBuilder(SQLServerSingleApplyFlowParamBuilder):
    controller = SqlserverController.ha_cluster_apply_scene

    def format_cluster_domains(self) -> List[Dict[str, str]]:
        db_module_name = DBModule.objects.get(db_module_id=self.ticket_data["db_module_id"]).db_module_name
        db_app_abbr = get_db_app_abbr(self.ticket_data["bk_biz_id"])
        return [
            {
                "name": domain["key"],
                "immutable_domain": MASTER_DOMAIN_INITIAL_VALUE.format(
                    db_module_name=db_module_name, db_app_abbr=db_app_abbr, cluster_name=domain["key"]
                ).replace("_", "-"),
                "slave_domain": SLAVE_DOMAIN_INITIAL_VALUE.format(
                    db_module_name=db_module_name, db_app_abbr=db_app_abbr, cluster_name=domain["key"]
                ).replace("_", "-"),
            }
            for domain in self.ticket_data["domains"]
        ]

    @classmethod
    def insert_ip_into_apply_infos(cls, ticket_data, infos: List[Dict]):
        backend_nodes = ticket_data["nodes"]["backend"]
        for index, apply_info in enumerate(infos):
            # 每组集群需要两个后端 IP 和两个 Proxy IP
            start, end = index * 2, (index + 1) * 2
            apply_info["mssql_master_host"] = backend_nodes[start:end][0]
            apply_info["mssql_slave_host"] = backend_nodes[start:end][1]


class SQLServerHaApplyResourceParamBuilder(SQLServerSingleApplyResourceParamBuilder):
    def format(self):
        super().format()

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        infos = next_flow.details["ticket_data"]["infos"]
        SQLServerHAApplyFlowParamBuilder.insert_ip_into_apply_infos(self.ticket.details, infos)
        next_flow.details["ticket_data"].update(infos=infos)
        next_flow.save(update_fields=["details"])


@BuilderFactory.register(
    TicketType.SQLSERVER_HA_APPLY, is_apply=True, cluster_type=ClusterType.SqlserverHA, iam=ActionEnum.SQLSERVER_APPLY
)
class SQLServerHAApplyFlowBuilder(SQLServerSingleApplyFlowBuilder):
    serializer = SQLServerHAApplyDetailSerializer
    inner_flow_builder = SQLServerHAApplyFlowParamBuilder
    inner_flow_name = _("SQLServer 高可用部署执行")
    resource_apply_builder = SQLServerHaApplyResourceParamBuilder
    # 标记集群类型
    cluster_type = ClusterType.SqlserverHA

    def patch_ticket_detail(self):
        # 补充数据库版本和字符集
        super().patch_ticket_detail()
