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
import logging
import random
import string

from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import DBPrivSecurityType
from backend.configuration.handlers.password import DBPasswordHandler
from backend.db_meta.enums import ClusterType
from backend.db_services.dbbase.constants import DORIS_DEFAULT_HTTP_PORT, DORIS_DEFAULT_QUERY_PORT
from backend.flow.consts import DORIS_DEFAULT_INSTANCE_NUM
from backend.flow.engine.controller.doris import DorisController
from backend.ticket import builders
from backend.ticket.builders.common import constants
from backend.ticket.builders.common.bigdata import BaseDorisTicketFlowBuilder, BigDataApplyDetailsSerializer
from backend.ticket.builders.common.constants import BigDataRole
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class DorisApplyDetailSerializer(BigDataApplyDetailsSerializer):
    http_port = serializers.IntegerField(help_text=_("http端口"), default=DORIS_DEFAULT_HTTP_PORT)
    query_port = serializers.IntegerField(help_text=_("输入端口"), default=DORIS_DEFAULT_QUERY_PORT)

    def validate(self, attrs):
        """
        doris上架限制:
        1. 主机角色互斥
        2. follower数量必须为3台，只能替换，无法扩缩容
        3. observer可选项 若选至少需要2台
        3. hot/clod 至少存在2台
        """

        # 判断主机角色是否互斥
        super().validate(attrs)

        # 判断域名
        super().validate_domain(ClusterType.Doris, attrs["cluster_name"], attrs["db_app_abbr"])

        # 判断端口范围，及9020,901互斥
        for port_name in ["http_port", "query_port"]:
            port = attrs[port_name]
            if port > constants.DORIS_PORT_END or port < constants.DORIS_PORT_START:
                raise serializers.ValidationError(_("端口号必须在5000到65535之间"))
            if port in constants.DORIS_INVALID_PORTS:
                raise serializers.ValidationError(_("端口号{}不可用").format(port))

        # 判断follower节点是否为3台
        follower_node_count = self.get_node_count(attrs, BigDataRole.Doris.FOLLOWER.value)
        if follower_node_count != constants.DORIS_FOLLOWER_NEED:
            raise serializers.ValidationError(_("follower节点数不为3台! 请保证follower的部署节点数等于为3"))

        # 判断observer是否选择，若选至少需要2台
        observer_node_count = self.get_node_count(attrs, BigDataRole.Doris.OBSERVER.value)
        if constants.DORIS_OBSERVER_ZERO < observer_node_count < constants.DORIS_OBSERVER_MIN:
            raise serializers.ValidationError(_("observer节点数小于2台! 请保证observer的部署节点数至少为2"))

        # 冷热 数据节点必选1种以上， # 每个角色至少需要2台
        hot_node_count = self.get_node_count(attrs, BigDataRole.Doris.HOT.value)
        cold_node_count = self.get_node_count(attrs, BigDataRole.Doris.COLD.value)

        total_nodes = hot_node_count + cold_node_count
        if not total_nodes:
            raise serializers.ValidationError(_("请保证冷/热节点必选1种以上"))
        if not (hot_node_count >= constants.DORIS_HOT_COLD_LIMIT or cold_node_count >= constants.DORIS_HOT_COLD_LIMIT):
            raise serializers.ValidationError(_("请保证部署节点的角色为2以上"))

        return attrs


class DorisApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = DorisController.doris_apply_scene

    def format_ticket_data(self):
        """ """
        self.ticket_data.update(
            {
                # doris 用户名首位需要字母
                "username": random.choice(string.ascii_letters) + get_random_string(7),
                "password": DBPasswordHandler.get_random_password(security_type=DBPrivSecurityType.DORIS_PASSWORD),
                "domain": f"doris.{self.ticket_data['cluster_name']}.{self.ticket_data['db_app_abbr']}.db",
            }
        )


class DorisApplyResourceParamBuilder(builders.ResourceApplyParamBuilder):
    @classmethod
    def fill_instance_num(cls, next_flow_data, ticket_data, nodes_key):
        """对doris的hot和cold角色填充实例数"""
        for role in ["hot", "cold"]:
            if role not in next_flow_data[nodes_key]:
                continue

            for node in next_flow_data["nodes"][role]:
                node["instance_num"] = ticket_data["resource_spec"][role].get(
                    "instance_num", DORIS_DEFAULT_INSTANCE_NUM
                )

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        self.fill_instance_num(next_flow.details["ticket_data"], self.ticket_data, nodes_key="nodes")
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.DORIS_APPLY, is_apply=True, cluster_type=ClusterType.Doris)
class DorisApplyFlowBuilder(BaseDorisTicketFlowBuilder):
    serializer = DorisApplyDetailSerializer
    inner_flow_builder = DorisApplyFlowParamBuilder
    inner_flow_name = _("DORIS集群部署")
    resource_apply_builder = DorisApplyResourceParamBuilder
