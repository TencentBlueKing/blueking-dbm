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
import csv
import datetime
from io import StringIO

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.constants import MYSQL_BINLOG_ROLLBACK, FlashbackBuildType
from backend.ticket.builders.common.field import DBTimezoneField
from backend.ticket.builders.mysql.base import (
    BaseMySQLHATicketFlowBuilder,
    DBTableField,
    MySQLBaseOperateDetailSerializer,
)
from backend.ticket.constants import FlowRetryType, TicketType
from backend.utils.time import datetime2str, str2datetime


class MySQLFlashbackDetailSerializer(MySQLBaseOperateDetailSerializer):
    class FlashbackSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        start_time = DBTimezoneField(help_text=_("开始时间"))
        end_time = DBTimezoneField(help_text=_("结束时间"), allow_blank=True)
        databases = serializers.ListField(help_text=_("目标库列表"), child=DBTableField(db_field=True))
        databases_ignore = serializers.ListField(help_text=_("忽略库列表"), child=DBTableField(db_field=True))
        tables = serializers.ListField(help_text=_("目标table列表"), child=DBTableField())
        tables_ignore = serializers.ListField(help_text=_("忽略table列表"), child=DBTableField())
        mysqlbinlog_rollback = serializers.CharField(
            help_text=_("flashback工具地址"), default=MYSQL_BINLOG_ROLLBACK, required=False
        )
        recored_file = serializers.CharField(help_text=_("记录文件"), required=False, default="")
        rows_filter = serializers.CharField(help_text=_("待闪回记录"), required=False, default="")
        direct_write_back = serializers.BooleanField(help_text=_("是否覆盖原始数据"), required=False, default=False)

    infos = serializers.ListSerializer(help_text=_("flashback信息"), child=FlashbackSerializer(), allow_empty=False)
    force = serializers.BooleanField(help_text=_("是否强制执行"), required=False, default=False)
    flashback_type = serializers.ChoiceField(help_text=_("闪回方式"), choices=FlashbackBuildType.get_choices())

    def validate_flash_time(self, attrs):
        # 校验start time和end time的合法性
        for info in attrs["infos"]:
            now = datetime.datetime.now(timezone.utc)
            info["end_time"] = info["end_time"] or datetime2str(now)
            start_time, end_time = str2datetime(info["start_time"]), str2datetime(info["end_time"])
            if start_time > end_time or start_time > now or end_time > now:
                raise serializers.ValidationError(
                    _("flash的起止时间{}--{}不合法，请保证开始时间小于结束时间，并且二者不大于当前时间").format(start_time, end_time)
                )

    def validate_rows_filter(self, attrs):
        if attrs["flashback_type"] not in FlashbackBuildType.get_values():
            raise serializers.ValidationError(_("不支持的闪回方式{}").format(attrs["flashback_type"]))
        # 校验待闪回记录信息
        if attrs["flashback_type"] != FlashbackBuildType.RECORD_FLASHBACK:
            for info in attrs["infos"]:
                if info["rows_filter"]:
                    raise serializers.ValidationError(_("库表闪回不支持rows_filter参数"))
            return attrs

        for info in attrs["infos"]:
            if not info["rows_filter"]:
                raise serializers.ValidationError(_("记录级闪回缺少rows_filter参数"))
            info["rows_filter"] = info["rows_filter"].replace(" ", "")
            try:
                # 使用 StringIO 将字符串转换为类似文件的对象
                csv_file = StringIO(info["rows_filter"])
                csv_reader = csv.reader(csv_file)
                # 获取头部并计算列数
                headers = next(csv_reader, None)
                if headers is None:
                    raise serializers.ValidationError(_("CSV file is empty"))
                # 校验库表是否存在字段名
                RemoteServiceHandler(bk_biz_id=self.context["bk_biz_id"]).validate_table_fields(info, headers)
                expected_column_count = len(headers)
                # 验证每一行的数据长度是否与头部长度一致
                for row_number, row in enumerate(csv_reader, start=2):
                    if len(row) != expected_column_count:
                        raise serializers.ValidationError(
                            _("字段个数 {} 与数据列数不匹配 {}.").format(row_number, expected_column_count)
                        )

            except csv.Error:
                raise serializers.ValidationError(_("输入内容不符合csv格式"))

    def check_flashback_database_result(self, attrs):
        # 校验flash的库表选择器
        RemoteServiceHandler(bk_biz_id=self.context["bk_biz_id"]).check_flashback_database(attrs["infos"])

        for info in attrs["infos"]:
            if info.get("message"):
                raise serializers.ValidationError(_(info["message"]))

    def validate(self, attrs):
        # 校验闪回的时间
        self.validate_flash_time(attrs)
        # 校验集群是否可用，集群类型为高可用
        super(MySQLFlashbackDetailSerializer, self).validate_cluster_can_access(attrs)
        # 库表校验结果判断
        self.check_flashback_database_result(attrs)
        # 校验待闪回记录格式与字段是否存在
        self.validate_rows_filter(attrs)

        return attrs


class MySQLFlashbackFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_flashback_scene


@builders.BuilderFactory.register(TicketType.MYSQL_FLASHBACK)
class MySQLFlashbackFlowBuilder(BaseMySQLHATicketFlowBuilder):
    serializer = MySQLFlashbackDetailSerializer
    inner_flow_builder = MySQLFlashbackFlowParamBuilder
    inner_flow_name = _("闪回执行")
    retry_type = FlowRetryType.MANUAL_RETRY
