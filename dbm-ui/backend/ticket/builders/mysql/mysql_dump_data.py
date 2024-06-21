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

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_services.mysql.sql_import.constants import BKREPO_DBCONSOLE_DUMPFILE_PATH, SQLCharset
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import (
    BaseMySQLTicketFlowBuilder,
    DBTableField,
    MySQLBaseOperateDetailSerializer,
)
from backend.ticket.constants import TicketType


class MySQLDumpDataDetailSerializer(MySQLBaseOperateDetailSerializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    charset = serializers.ChoiceField(help_text=_("字符集"), choices=SQLCharset.get_choices())
    where = serializers.CharField(help_text=_("where条件"), required=False, allow_null=True, allow_blank=True)
    databases = serializers.ListField(help_text=_("导出库列表"), child=DBTableField(db_field=True))
    tables = serializers.ListField(help_text=_("目标table列表"), child=DBTableField())
    tables_ignore = serializers.ListField(help_text=_("忽略table列表"), child=DBTableField(), required=False, default=[])
    dump_schema = serializers.BooleanField(help_text=_("是否导出表结构"))
    dump_data = serializers.BooleanField(help_text=_("是否导出表数据"))
    force = serializers.BooleanField(help_text=_("是否强制执行"), default=False)


class MySQLDumpDataFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.dbconsole_dump_scene

    def post_callback(self):
        # 往flow的detail中写入制品库的下载链接
        flow = self.ticket.current_flow()
        dump_file_name = f"{flow.flow_obj_id}_dbm_console_dump.sql.zip"
        flow.details["ticket_data"].update(
            dump_file_name=dump_file_name, dump_file_path=f"{BKREPO_DBCONSOLE_DUMPFILE_PATH}/{dump_file_name}"
        )
        flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.MYSQL_DUMP_DATA)
class MySQLDumpDataFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLDumpDataDetailSerializer
    inner_flow_builder = MySQLDumpDataFlowParamBuilder
    inner_flow_name = _("数据导出执行")
