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

import json
import logging

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster
from backend.db_services.mysql.sql_import.constants import SQLExecuteTicketMode
from backend.db_services.mysql.sql_import.handlers import SQLHandler
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.engine.controller.mysql import MySQLController
from backend.flow.models import FlowNode, FlowTree
from backend.flow.plugins.components.collections.mysql.semantic_check import SemanticCheckComponent
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.exceptions import TicketBaseException
from backend.ticket.models import Flow

logger = logging.getLogger("root")


class MysqlSqlImportDetailSerializer(MySQLBaseOperateDetailSerializer):
    root_id = serializers.CharField(help_text=_("语义执行的流程ID"))

    def validate(self, attrs):
        root_id = attrs["root_id"]
        first_act_node_id = FlowNode.objects.filter(root_id=root_id).first().node_id
        try:
            details = BambooEngine(root_id=root_id).get_node_input_data(node_id=first_act_node_id).data["global_data"]
        except KeyError:
            raise serializers.ValidationError(_("无法获取语义执行id:{}的上下文数据，请检查语义执行任务是否成功完成").format(root_id))

        super().validate(details)
        return attrs


class MysqlSqlImportItsmParamBuilder(builders.ItsmParamBuilder):
    """SQL导入审批单据参数"""

    def get_params(self):
        params = super().get_params()

        # 添加语义执行结果的链接
        root_id = self.ticket.details["root_id"]
        semantic_url = f"{env.BK_SAAS_HOST}/database/{self.ticket.bk_biz_id}/mission-details/{root_id}/"
        params["dynamic_fields"].append({"name": _("模拟执行链接"), "type": "LINK", "value": semantic_url})

        return params


class MysqlSqlImportBackUpFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_ha_db_table_backup_scene

    def format_ticket_data(self):
        backup_infos_list = []
        for backup_info in self.ticket_data.pop("backup"):
            backup_infos_list.extend(
                [{"cluster_id": cluster_id, **backup_info} for cluster_id in self.ticket_data["cluster_ids"]]
            )

        self.ticket_data["infos"] = backup_infos_list


class MysqlSqlImportFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_import_sqlfile_scene

    def format_ticket_data(self):
        pass


@builders.BuilderFactory.register(TicketType.MYSQL_IMPORT_SQLFILE)
class MysqlSqlImportFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MysqlSqlImportDetailSerializer
    editable = False

    @classmethod
    def patch_sqlimport_ticket_detail(cls, ticket, cluster_type):
        # 移除语义执行缓存
        root_id = ticket.details["root_id"]
        handler = SQLHandler(bk_biz_id=ticket.bk_biz_id, context={"user": ticket.creator}, cluster_type=cluster_type)
        handler.delete_user_semantic_tasks(task_ids=[root_id])

        # 为语义执行的FlowTree关联单据
        flow_tree = FlowTree.objects.get(root_id=root_id)
        flow_tree.uid = ticket.id
        flow_tree.save()

        # 获取语义执行的details的输入数据
        first_act_node_id = FlowNode.objects.filter(root_id=root_id).first().node_id
        try:
            details = BambooEngine(root_id=root_id).get_node_input_data(node_id=first_act_node_id).data["global_data"]
        except KeyError:
            raise TicketBaseException(_("模拟执行的pipeline数据还未准备好，请检查celery状态并稍后重试单据。"))
        else:
            # 移除无用的字段，避免污染ticket的details
            pop_fields = ["uid", "ticket_type"]
            [details.pop(field, None) for field in pop_fields]

        # 补充集群信息和node_id
        cluster_ids = details["cluster_ids"]
        semantic_node_id = handler.get_node_id_by_component(flow_tree.tree, SemanticCheckComponent.code)
        details.update(
            semantic_node_id=semantic_node_id,
            clusters={cluster.id: cluster.to_dict() for cluster in Cluster.objects.filter(id__in=cluster_ids)},
        )

        ticket.details.update(details)
        ticket.save(update_fields=["details"])

    def patch_ticket_detail(self):
        self.patch_sqlimport_ticket_detail(ticket=self.ticket, cluster_type=DBType.MySQL)

    def init_ticket_flows(self):
        """
        sql导入根据执行模式可分为三种执行流程：
        手动：语义检查-->单据审批-->手动确认-->(备份)--->sql导入
        自动：语义检查-->单据审批-->(备份)--->sql导入
        定时：语义检查-->单据审批-->定时触发-->(备份)--->sql导入
        """

        flows = [
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.DESCRIBE_TASK.value,
                details=MysqlSqlImportFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("SQL模拟执行状态查询"),
            ),
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.BK_ITSM.value,
                details=MysqlSqlImportItsmParamBuilder(self.ticket).get_params(),
                flow_alias=_("单据审批"),
            ),
        ]

        mode = self.ticket.details["ticket_mode"]["mode"]
        if mode == SQLExecuteTicketMode.MANUAL.value:
            flows.append(Flow(ticket=self.ticket, flow_type=FlowType.PAUSE.value, flow_alias=_("人工确认执行")))
        elif mode == SQLExecuteTicketMode.TIMER.value:
            flows.append(Flow(ticket=self.ticket, flow_type=FlowType.TIMER.value, flow_alias=_("定时执行")))

        if self.ticket.details.get("backup"):
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.INNER_FLOW.value,
                    details=MysqlSqlImportBackUpFlowParamBuilder(self.ticket).get_params(),
                    retry_type=FlowRetryType.MANUAL_RETRY.value,
                    flow_alias=_("库表备份"),
                )
            )

        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=MysqlSqlImportFlowParamBuilder(self.ticket).get_params(),
                retry_type=FlowRetryType.MANUAL_RETRY.value,
                flow_alias=_("变更SQL执行"),
            )
        )

        Flow.objects.bulk_create(flows)
        return list(Flow.objects.filter(ticket=self.ticket))

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = [_("SQL模拟执行状态查询"), _("单据审批"), _("库表备份(可选)"), _("变更SQL执行")]
        return flow_desc
