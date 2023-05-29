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
from backend.db_meta.models import Cluster
from backend.db_services.mysql.sql_import.constants import SQLExecuteTicketMode
from backend.db_services.mysql.sql_import.dataclass import SemanticOperateMeta
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

    def format(self):
        self.details.pop("execute_sql_files")
        self.details.pop("execute_db_infos")

        self.details[_("字符集")] = self.details.pop("charset")
        self.details[_("sql文件路径")] = self.details.pop("path")
        self.details[_("集群ID")] = self.details.pop("cluster_ids")
        self.details[_("执行模式")] = self.details.pop("ticket_mode")
        self.details[_("sql导入模式")] = self.details.pop("import_mode")
        self.details[_("模拟执行node_id")] = self.details.pop("semantic_node_id")
        self.details[_("模拟执行root_id")] = self.details.pop("root_id")
        self.details[_("业务ID")] = self.details.pop("bk_biz_id")
        self.details[_("创建人")] = self.details.pop("created_by")
        self.details[_("高危信息提示")] = self.details.pop("highrisk_warnings")

        execute_objects = self.details.pop("execute_objects")
        for index, sql_obj in enumerate(execute_objects):
            sql_obj[_("sql文件名")] = sql_obj.pop("sql_file")
            sql_obj[_("目标变更db")] = sql_obj.pop("dbnames")
            sql_obj[_("忽略db")] = sql_obj.pop("ignore_dbnames")
            execute_objects[index] = json.dumps(sql_obj, ensure_ascii=False)

        sql_execute_info = "\n".join(execute_objects)
        self.details[_("sql执行体信息")] = f"[\n{sql_execute_info}\n]"

        backup_objects = self.details.pop("backup", [])
        for index, backup_obj in enumerate(backup_objects):
            backup_obj[_("备份源")] = backup_obj.pop("backup_on")
            backup_obj[_("备份匹配DB列表")] = backup_obj.pop("db_patterns")
            backup_obj[_("备份匹配Table列表")] = backup_obj.pop("table_patterns")
            backup_objects[index] = json.dumps(backup_obj, ensure_ascii=False)

        backup_info = "\n".join(backup_objects)
        self.details[_("sql备份信息")] = f"[\n{backup_info}\n]"

    def get_params(self):
        params = super().get_params()

        # 添加语义执行结果的链接
        root_id = self.details[_("模拟执行root_id")]
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

    def patch_ticket_detail(self):
        # 移除语义执行缓存
        root_id = self.ticket.details["root_id"]
        handler = SQLHandler(bk_biz_id=self.ticket.bk_biz_id, context={"user": self.ticket.creator})
        handler.delete_user_semantic_tasks(semantic=SemanticOperateMeta(task_ids=[root_id]))

        # 为语义执行的FlowTree关联单据
        flow_tree = FlowTree.objects.get(root_id=root_id)
        flow_tree.uid = self.ticket.id
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
            __ = [details.pop(field, None) for field in pop_fields]

        # 补充集群信息和node_id
        cluster_ids = details["cluster_ids"]
        semantic_node_id = handler._get_node_id_by_component(flow_tree, SemanticCheckComponent.code)
        details.update(
            semantic_node_id=semantic_node_id,
            clusters={cluster.id: cluster.to_dict() for cluster in Cluster.objects.filter(id__in=cluster_ids)},
        )

        self.ticket.details.update(details)
        self.ticket.save(update_fields=["details"])

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
