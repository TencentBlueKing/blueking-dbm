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
import re
import time

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.models import AppCache, Cluster
from backend.db_services.mysql.sql_import.constants import BKREPO_DBCONSOLE_DUMPFILE_PATH, SQLCharset
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import TicketBaseValidateSerializerMixin
from backend.ticket.builders.mysql.base import (
    BaseMySQLTicketFlowBuilder,
    DBTableField,
    MySQLBaseOperateDetailSerializer,
)
from backend.ticket.constants import FlowType, TicketFlowStatus, TicketType
from backend.ticket.models import Flow
from blue_krill.data_types.enum import EnumField, StrStructuredEnum

# 只剥语句首尾注释，避免把字符串字面量里的 -- / /* 误删
_LEADING_BLOCK_COMMENT_RE = re.compile(r"^/\*.*?\*/", re.DOTALL)
_LEADING_LINE_COMMENT_RE = re.compile(r"^(?:--|#)[^\n]*(?:\n|$)")
_INTO_OUTFILE_RE = re.compile(r"\binto\s+(outfile|dumpfile)\b", re.IGNORECASE)


class MySQLDataExportMode(StrStructuredEnum):
    """数据导出方式。dump 为现有库表导出，sql 为按查询语句导出。"""

    DUMP = EnumField("dump", _("库表导出"))
    SQL = EnumField("sql", _("SQL导出"))


def is_mysql_sql_export(details: dict) -> bool:
    return details.get("export_mode") == MySQLDataExportMode.SQL.value


def _strip_leading_sql_noise(text: str) -> str:
    while text:
        block_match = _LEADING_BLOCK_COMMENT_RE.match(text)
        if block_match:
            text = text[block_match.end() :].strip()
            continue
        line_match = _LEADING_LINE_COMMENT_RE.match(text)
        if line_match:
            text = text[line_match.end() :].strip()
            continue
        break
    return text


def _strip_trailing_sql_noise(text: str) -> str:
    while text:
        stripped = text.rstrip()
        if stripped.endswith("*/"):
            start = stripped.rfind("/*")
            if start < 0:
                return stripped
            text = stripped[:start].rstrip()
            continue
        lines = stripped.split("\n")
        last = lines[-1].lstrip()
        if last.startswith("--") or last.startswith("#"):
            text = "\n".join(lines[:-1]).rstrip()
            continue
        return stripped
    return text


def prepare_export_sql(sql: str) -> str:
    """整理 SQL 导出语句：去掉首尾注释和末尾分号，并限制为单条 SELECT。"""
    text = _strip_leading_sql_noise((sql or "").strip())
    while text:
        stripped = _strip_trailing_sql_noise(text)
        if stripped.endswith(";"):
            text = stripped[:-1].rstrip()
            continue
        text = stripped
        break
    if not text:
        raise serializers.ValidationError({"sql": _("SQL导出内容不能为空")})
    if ";" in text:
        raise serializers.ValidationError({"sql": _("SQL导出仅支持单条查询语句")})
    if _INTO_OUTFILE_RE.search(text):
        raise serializers.ValidationError({"sql": _("SQL导出不允许使用 INTO OUTFILE / INTO DUMPFILE")})
    first_token = text.split(None, 1)[0].lower()
    if first_token not in ("select", "with"):
        raise serializers.ValidationError({"sql": _("SQL导出仅支持 SELECT 查询")})
    return text


class MySQLDumpDataDetailSerializer(MySQLBaseOperateDetailSerializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    charset = serializers.ChoiceField(help_text=_("字符集"), choices=SQLCharset.get_choices())
    export_mode = serializers.ChoiceField(
        help_text=_("导出方式：dump 库表导出，sql SQL导出"),
        choices=MySQLDataExportMode.get_choices(),
        required=False,
        default=MySQLDataExportMode.DUMP.value,
    )
    where = serializers.CharField(help_text=_("where条件"), required=False, allow_null=True, allow_blank=True)
    databases = serializers.ListField(help_text=_("导出库列表"), child=serializers.CharField(), required=False)
    tables = serializers.ListField(help_text=_("目标table列表"), child=serializers.CharField(), required=False)
    tables_ignore = serializers.ListField(help_text=_("忽略table列表"), child=DBTableField(), required=False, default=[])
    dump_schema = serializers.BooleanField(help_text=_("是否导出表结构"), required=False)
    dump_data = serializers.BooleanField(help_text=_("是否导出表数据"), required=False)
    sql = serializers.CharField(help_text=_("导出SQL，仅 SQL 导出时必填"), required=False, allow_blank=True, allow_null=True)
    force = serializers.BooleanField(help_text=_("是否强制执行"), default=False)

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        data["is_external"] = getattr(self.context["request"], "is_external", False)
        return data

    def validate(self, attrs):
        if is_mysql_sql_export(attrs):
            return self._validate_sql_export(attrs)
        self._require_dump_fields(attrs)
        return super().validate(attrs)

    def _require_dump_fields(self, attrs):
        errors = {}
        for field in ("databases", "tables", "dump_schema", "dump_data"):
            if field not in attrs:
                errors[field] = _("该字段是必填项。")
        if attrs.get("databases") == []:
            errors["databases"] = _("导出库列表不能为空")
        if attrs.get("tables") == []:
            errors["tables"] = _("目标table列表不能为空")
        if errors:
            raise serializers.ValidationError(errors)

    def _validate_sql_export(self, attrs):
        # TenDB Cluster 复用本序列化器，SQL 导出只对 MySQL 数据导出开放
        if self.context.get("ticket_type") != TicketType.MYSQL_DUMP_DATA:
            raise serializers.ValidationError(_("当前仅 MySQL 数据导出支持 SQL 导出"))
        attrs["sql"] = prepare_export_sql(attrs.get("sql"))
        # 跳过库表 dump 的 where 校验器，执行 flow 尚未接入
        attrs = TicketBaseValidateSerializerMixin.validate(self, attrs)
        self.validate_cluster_can_access(attrs)
        return attrs


class MySQLDumpDataItsmMaintainerFlowParamsBuilder(builders.ItsmParamBuilder):
    def get_approvers(self):
        approvers = AppCache.get_app_attr_from_cc(self.ticket.bk_biz_id, attr_name="bk_biz_maintainer")
        return approvers or "admin"


class MySQLDumpDataItsmProductorFlowParamsBuilder(builders.ItsmParamBuilder):
    def get_approvers(self):
        approvers = AppCache.get_app_attr_from_cc(self.ticket.bk_biz_id, attr_name="bk_biz_productor")
        return approvers or "admin"


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
    itsm_flow_maintainer_builder = MySQLDumpDataItsmMaintainerFlowParamsBuilder
    itsm_flow_productor_builder = MySQLDumpDataItsmProductorFlowParamsBuilder
    validator = MySQLController.dbconsole_dump_scene.validator
    editable = False

    def init_ticket_flows(self):
        flows = []
        # 二级审批
        if self.need_itsm:
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.BK_ITSM.value,
                    details=self.itsm_flow_maintainer_builder(self.ticket).get_params(),
                    flow_alias=_("运维人员审批"),
                )
            )
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.BK_ITSM.value,
                    details=self.itsm_flow_productor_builder(self.ticket).get_params(),
                    flow_alias=_("产品人员审批"),
                )
            )
        # 人工确认
        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.PAUSE.value,
                details=self.pause_node_builder(self.ticket).get_params(),
                flow_alias=_("人工确认"),
            ),
        )
        # SQL 导出的执行 flow 还没完成，先不挂 inner flow，避免走到库表 dump
        if not is_mysql_sql_export(self.ticket.details):
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.INNER_FLOW.value,
                    details=self.inner_flow_builder(self.ticket).get_params(),
                    flow_alias=self.inner_flow_name,
                    retry_type=self.retry_type,
                )
            )

        Flow.objects.bulk_create(flows)
        return list(Flow.objects.filter(ticket=self.ticket))

    @property
    def need_itsm(self):
        # SQL 导出属于数据导出，固定走运维 + 产品审批
        if is_mysql_sql_export(self.ticket.details):
            return True
        # 1. 导出数据和表结构 ：运维人员 + 产品人员 审批
        # 2. 导出数据 ：运维人员 + 产品人员 审批
        # 3. 导出表结构 ：正常情况 - 不需要审批，PO环境 - 运维人员 + 产品人员 审批
        return self.ticket.details["dump_data"] or self.ticket.details["is_external"]

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = [_("运维人员审批"), _("产品人员审批"), _("人工确认"), _("数据导出执行")]
        return flow_desc
