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
import time

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.models import AppCache, Cluster
from backend.db_services.mysql.sql_import.constants import BKREPO_DBCONSOLE_DUMPFILE_PATH, SQLCharset
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import (
    BaseMySQLTicketFlowBuilder,
    DBTableField,
    MySQLBaseOperateDetailSerializer,
)
from backend.ticket.constants import TicketFlowStatus, TicketType


class MySQLDumpDataDetailSerializer(MySQLBaseOperateDetailSerializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    charset = serializers.ChoiceField(help_text=_("字符集"), choices=SQLCharset.get_choices())
    where = serializers.CharField(help_text=_("where条件"), required=False, allow_null=True, allow_blank=True)
    databases = serializers.ListField(help_text=_("导出库列表"), child=serializers.CharField())
    tables = serializers.ListField(help_text=_("目标table列表"), child=serializers.CharField())
    tables_ignore = serializers.ListField(help_text=_("忽略table列表"), child=DBTableField(), required=False, default=[])
    dump_schema = serializers.BooleanField(help_text=_("是否导出表结构"))
    dump_data = serializers.BooleanField(help_text=_("是否导出表数据"))
    force = serializers.BooleanField(help_text=_("是否强制执行"), default=False)

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        data["is_external"] = getattr(self.context["request"], "is_external", False)
        return data


class MySQLDumpDataItsmFlowParamsBuilder(builders.ItsmParamBuilder):
    def get_approvers(self):
        bk_biz_maintainer = AppCache.get_app_attr_from_cc(self.ticket.bk_biz_id, attr_name="bk_biz_maintainer")
        return bk_biz_maintainer or super().get_approvers()


class MySQLDumpDataFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.dbconsole_dump_scene

    def format_ticket_data(self):
        cluster = Cluster.objects.get(id=self.ticket_data["cluster_id"])
        dump_file_name = f"{cluster.immute_domain}_{int(time.time())}_dbm_console_dump.sql"
        self.ticket_data["dump_file_name"] = dump_file_name

    def post_callback(self):
        flow = self.ticket.current_flow()
        # 如果流程树运行不为成功，则忽略
        if flow.status != TicketFlowStatus.SUCCEEDED:
            return
        # 往flow的detail中写入制品库的下载链接
        dump_file_name = f"{flow.details['ticket_data']['dump_file_name']}.zip"
        flow.details["ticket_data"].update(
            dump_file_name=dump_file_name,
            dump_file_path=f"{BKREPO_DBCONSOLE_DUMPFILE_PATH.format(biz=self.ticket.bk_biz_id)}/{dump_file_name}",
        )
        flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.MYSQL_DUMP_DATA)
class MySQLDumpDataFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLDumpDataDetailSerializer
    inner_flow_builder = MySQLDumpDataFlowParamBuilder
    inner_flow_name = _("数据导出执行")
    itsm_flow_builder = MySQLDumpDataItsmFlowParamsBuilder

    @property
    def need_itsm(self):
        # 1. 导出数据和表结构 ：运维人员审批
        # 2.导出数据 ：运维人员审批
        # 3.导出表结构 ：正常情况 - 不需要审批，PO环境 - 运维人员审批
        return self.ticket.details["dump_data"] or self.ticket.details["is_external"]
