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
import re
import time

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.core.storages.storage import get_storage
from backend.db_meta.models import AppCache, Cluster
from backend.db_proxy.constants import ExtensionType
from backend.db_proxy.models import DBExtension
from backend.db_services.mysql.sql_import.constants import (
    BKREPO_DBCONSOLE_DUMPFILE_PATH,
    BKREPO_SQLFILE_PATH,
    SQLCharset,
)
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import (
    BaseMySQLTicketFlowBuilder,
    DBTableField,
    MySQLBaseOperateDetailSerializer,
)
from backend.ticket.constants import FlowType, TicketFlowStatus, TicketType
from backend.ticket.models import Flow

EXPORT_MODE_TABLE = "table"
EXPORT_MODE_SQL = "sql"
RESULT_FORMAT_TXT = "txt"
RESULT_FORMAT_CSV = "csv"
SQL_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+\.sql$")
# 单据详情展示的查询SQL上限，超过则截断，避免大文件撑爆单据详情
MAX_SQL_CONTENT_SIZE = 2 * 1024 * 1024
SQL_CONTENT_TRUNCATED_TIP = _("\n... SQL文件过大，仅展示部分查询SQL")

logger = logging.getLogger("root")


class MySQLDumpDataDetailSerializer(MySQLBaseOperateDetailSerializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    export_mode = serializers.ChoiceField(
        help_text=_("导出模式"),
        choices=[(EXPORT_MODE_TABLE, _("按库表")), (EXPORT_MODE_SQL, _("按SQL"))],
        required=False,
        default=EXPORT_MODE_TABLE,
    )
    charset = serializers.ChoiceField(
        help_text=_("字符集"),
        choices=SQLCharset.get_choices(),
        required=False,
        default=SQLCharset.DEFAULT.value,
    )
    where = serializers.CharField(help_text=_("where条件"), required=False, allow_null=True, allow_blank=True)
    databases = serializers.ListField(help_text=_("导出库列表"), child=serializers.CharField(), required=False)
    tables = serializers.ListField(help_text=_("目标table列表"), child=serializers.CharField(), required=False)
    tables_ignore = serializers.ListField(help_text=_("忽略table列表"), child=DBTableField(), required=False, default=[])
    dump_schema = serializers.BooleanField(help_text=_("是否导出表结构"), required=False)
    dump_data = serializers.BooleanField(help_text=_("是否导出表数据"), required=False)
    force = serializers.BooleanField(help_text=_("是否强制执行"), default=False)
    sql_path = serializers.CharField(help_text=_("SQL文件路径"), required=False, allow_blank=True, default="")
    sql_filename = serializers.CharField(help_text=_("SQL文件名"), required=False, allow_blank=True, default="")
    sql_sha256 = serializers.CharField(help_text=_("SQL文件SHA256"), required=False, allow_blank=True, default="")
    result_format = serializers.ChoiceField(
        help_text=_("结果格式"),
        choices=[(RESULT_FORMAT_TXT, RESULT_FORMAT_TXT), (RESULT_FORMAT_CSV, RESULT_FORMAT_CSV)],
        required=False,
        default=RESULT_FORMAT_TXT,
    )

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        data["is_external"] = getattr(self.context["request"], "is_external", False)
        return data

    def validate(self, attrs):
        mode = attrs.get("export_mode") or EXPORT_MODE_TABLE
        attrs["export_mode"] = mode
        if not attrs.get("charset"):
            attrs["charset"] = SQLCharset.DEFAULT.value
        if mode == EXPORT_MODE_SQL:
            self._validate_sql_shape(attrs)
            if attrs.get("result_format") == RESULT_FORMAT_CSV:
                self._require_dump_center(attrs)
        else:
            self._require_table_fields(attrs)
        return super().validate(attrs)

    def _require_table_fields(self, attrs):
        missing = {}
        if "databases" not in attrs:
            missing["databases"] = _("缺少导出库列表")
        if "tables" not in attrs:
            missing["tables"] = _("缺少目标table列表")
        if "dump_data" not in attrs:
            missing["dump_data"] = _("缺少是否导出表数据")
        if "dump_schema" not in attrs:
            missing["dump_schema"] = _("缺少是否导出表结构")
        if missing:
            raise serializers.ValidationError(missing)

    def _validate_sql_shape(self, attrs):
        filename = attrs.get("sql_filename") or ""
        if SQL_FILENAME_PATTERN.match(filename) is None:
            raise serializers.ValidationError({"sql_filename": _("文件名不合法")})
        bk_biz_id = self.context.get("bk_biz_id")
        expected = BKREPO_SQLFILE_PATH.format(biz=bk_biz_id)
        sql_path = (attrs.get("sql_path") or "").rstrip("/")
        attrs["sql_path"] = sql_path
        if not bk_biz_id or not self._sql_path_in_biz(sql_path, expected):
            raise serializers.ValidationError({"sql_path": _("路径不在本业务目录下")})
        if "cluster_id" not in attrs:
            raise serializers.ValidationError({"cluster_id": _("缺少集群ID")})

    def _require_dump_center(self, attrs):
        cluster = Cluster.objects.filter(id=attrs.get("cluster_id")).first()
        bk_cloud_id = getattr(cluster, "bk_cloud_id", None)
        dump_center = None
        if bk_cloud_id is not None:
            dump_center = DBExtension.get_latest_extension(
                bk_cloud_id=bk_cloud_id, extension_type=ExtensionType.CONSOLE_DUMP_CENTER
            )
        if not dump_center:
            raise serializers.ValidationError({"result_format": _("CSV 导出需要配置中转机")})

    @staticmethod
    def _sql_path_in_biz(sql_path, expected):
        if any(part in (".", "..") for part in sql_path.split("/")):
            return False
        return sql_path == expected or sql_path.startswith(expected + "/")


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
        # 数据导出
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
        # 1. 导出数据和表结构 ：运维人员 + 产品人员 审批
        # 2. 导出数据 ：运维人员 + 产品人员 审批
        # 3. 导出表结构 ：正常情况 - 不需要审批，PO环境 - 运维人员 + 产品人员 审批
        details = self.ticket.details
        if details.get("export_mode") == EXPORT_MODE_SQL:
            return True
        return bool(details.get("dump_data") or details.get("is_external"))

    def patch_ticket_detail(self):
        # 按SQL导出时，补充查询SQL(即SQL文件内容)到单据详情，便于详情页/审批时查看
        if self.ticket.details.get("export_mode") == EXPORT_MODE_SQL:
            self.ticket.details["sql_content"] = self.fetch_sql_content()
        super().patch_ticket_detail()

    def fetch_sql_content(self) -> str:
        """读取制品库中SQL文件的内容，作为单据详情的查询SQL。读取失败不影响提单，返回空串"""
        if self.ticket.details.get("export_mode") != EXPORT_MODE_SQL:
            return ""

        sql_filename = self.ticket.details.get("sql_filename") or ""
        sql_path = (self.ticket.details.get("sql_path") or "").rstrip("/")
        if not sql_filename or not sql_path:
            return ""

        full_path = f"{sql_path}/{sql_filename}"
        try:
            resp = get_storage().client.batch_download([full_path])
            if getattr(resp, "status_code", 200) != 200:
                logger.warning(_("读取SQL文件失败: %s"), full_path)
                return ""
            sql_content = resp.content or b""
        except Exception as err:  # pylint: disable=broad-except
            logger.warning(_("读取SQL文件失败: %s, 错误信息: %s"), full_path, err)
            return ""

        truncated = len(sql_content) > MAX_SQL_CONTENT_SIZE
        # 截断后按replace模式解码，避免末尾多字节字符被截断导致解码失败
        sql_content = sql_content[:MAX_SQL_CONTENT_SIZE].decode("utf-8", errors="replace")
        if truncated:
            sql_content += str(SQL_CONTENT_TRUNCATED_TIP)
        return sql_content

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = [_("运维人员审批"), _("产品人员审批"), _("人工确认"), _("数据导出执行")]
        return flow_desc
