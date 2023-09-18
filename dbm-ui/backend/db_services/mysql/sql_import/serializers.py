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
from datetime import datetime

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.constants import DATETIME_PATTERN
from backend.db_meta.enums import InstanceInnerRole
from backend.db_services.mysql.sql_import import mock_data
from backend.db_services.mysql.sql_import.constants import (
    BKREPO_SQLFILE_PATH,
    SQLCharset,
    SQLExecuteTicketMode,
    SQLImportMode,
)
from backend.exceptions import ValidationError
from backend.flow.models import StateType
from backend.ticket.constants import TicketType


class SQLGrammarCheckSerializer(serializers.Serializer):
    sql_content = serializers.CharField(help_text=_("sql语句"), required=False)
    sql_files = serializers.ListField(
        help_text=_("sql文件列表"), child=serializers.FileField(help_text=_("sql文件"), required=False), required=False
    )

    class Meta:
        swagger_schema_fields = {"example": mock_data.SQL_GRAMMAR_CHECK_REQUEST_DATA}

    def validate(self, attrs):
        if not (attrs.get("sql_content", None) or attrs.get("sql_files", None)):
            raise ValidationError(_("不允许sql_content和sql_file同时为空，请至少填写一项"))

        return attrs


class SQLGrammarCheckResultSerializer(serializers.Serializer):
    syntax_fails = serializers.ListField(help_text=_("语法错误"), allow_empty=True, allow_null=True)
    highrisk_warnings = serializers.ListField(help_text=_("高危警告"), allow_empty=True, allow_null=True)
    bancommand_warnings = serializers.ListField(help_text=_("禁止命令"), allow_empty=True, allow_null=True)


class SQLGrammarCheckResponseSerializer(serializers.Serializer):
    sql_file_name = serializers.DictField(help_text=_("语法检查结果"), child=SQLGrammarCheckResultSerializer())

    class Meta:
        swagger_schema_fields = {"example": mock_data.SQL_GRAMMAR_CHECK_RESPONSE_DATA}


class SQLSemanticCheckSerializer(serializers.Serializer):
    class ExecuteDBInfoSerializer(serializers.Serializer):
        dbnames = serializers.ListField(help_text=_("目标变更DB"), child=serializers.CharField())
        ignore_dbnames = serializers.ListField(help_text=_("忽略DB"), child=serializers.CharField())

    class SQLImportModeSerializer(serializers.Serializer):
        mode = serializers.ChoiceField(help_text=_("单据执行模式"), choices=SQLExecuteTicketMode.get_choices())
        trigger_time = serializers.CharField(help_text=_("定时任务触发时间"), required=False, allow_blank=True)

    class SQLImportBackUpSerializer(serializers.Serializer):
        backup_on = serializers.ChoiceField(choices=InstanceInnerRole.get_choices(), help_text=_("备份源"))
        db_patterns = serializers.ListField(help_text=_("匹配DB列表"), child=serializers.CharField())
        table_patterns = serializers.ListField(help_text=_("匹配Table列表"), child=serializers.CharField())
        ignore_dbs = serializers.ListField(
            help_text=_("忽略DB列表"), child=serializers.CharField(), required=False, default=[]
        )
        ignore_tables = serializers.ListField(
            help_text=_("忽略Table列表"), child=serializers.CharField(), required=False, default=[]
        )

    charset = serializers.ChoiceField(
        help_text=_("字符集"), required=False, choices=SQLCharset.get_choices(), default=SQLCharset.DEFAULT.value
    )
    path = serializers.CharField(help_text=_("SQL文件路径"), required=False, default=BKREPO_SQLFILE_PATH)
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
    execute_sql_files = serializers.ListField(help_text=_("sql执行文件"), child=serializers.CharField())
    execute_db_infos = serializers.ListSerializer(help_text=_("sql执行的DB信息"), child=ExecuteDBInfoSerializer())
    highrisk_warnings = serializers.DictField(help_text=_("高危信息提示"), required=False, default="")
    ticket_type = serializers.ChoiceField(help_text=_("单据类型"), choices=TicketType.get_choices())
    ticket_mode = SQLImportModeSerializer()
    import_mode = serializers.ChoiceField(help_text=_("sql导入模式"), choices=SQLImportMode.get_choices())
    backup = serializers.ListSerializer(help_text=_("备份信息"), child=SQLImportBackUpSerializer(), required=False)

    class Meta:
        swagger_schema_fields = {"example": mock_data.SQL_SEMANTIC_CHECK_REQUEST_DATA}

    def validate(self, attrs):
        # 验证trigger_time的格式合法性，不要等到创建单据的时候再验证
        if attrs["ticket_mode"] == SQLExecuteTicketMode.TIMER.value:
            trigger_time = attrs["ticket_mode"]["trigger_time"]
            try:
                datetime.strptime(trigger_time, DATETIME_PATTERN)
            except Exception as e:  # pylint: disable=broad-except
                raise serializers.Serializer(_("时间{}格式解析失败: {}，请按照{}格式输入时间").format(trigger_time, e, DATETIME_PATTERN))

        return attrs


class SQLSemanticCheckResponseSerializer(serializers.Serializer):
    root_id = serializers.CharField(help_text=_("流程id"))
    node_id = serializers.CharField(help_text=_("语义测试的node_id"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.SQL_SEMANTIC_CHECK_RESPONSE_DATA}


class SQLUserConfigSerializer(serializers.Serializer):
    root_id = serializers.CharField(help_text=_("流程id"))
    is_auto_commit = serializers.BooleanField(help_text=_("是否自动创建单据"), required=False, default=False)
    is_skip_pause = serializers.BooleanField(help_text=_("是否自动跳过确认"), required=False, default=False)

    class Meta:
        swagger_schema_fields = {"example": mock_data.SQL_TICKET_AUTO_COMMIT_REQUEST_DATA}


class QuerySQLUserConfigSerializer(serializers.Serializer):
    is_auto_commit = serializers.BooleanField(help_text=_("是否自动创建单据"))
    is_skip_pause = serializers.BooleanField(help_text=_("是否自动跳过确认"))

    class Meta:
        swagger_schema_fields = {"example": {"is_auto_commit": True, "is_skip_pause": True}}


class GetUserSemanticListSerializer(serializers.Serializer):
    # TODO 暂时不需要用户参数，后面可能会扩展
    # user = serializers.CharField(help_text=_("用户名"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.USER_SEMANTIC_LIST_REQUEST_DATA}


class GetUserSemanticListResponseSerializer(serializers.Serializer):
    class SemanticInfoSerializer(serializers.Serializer):
        root_id = serializers.CharField(help_text=_("流程id"))
        created_at = serializers.CharField(help_text=_("创建时间"))
        status = serializers.ChoiceField(help_text=_("执行状态"), choices=StateType.get_choices())

    semantic_list = serializers.ListSerializer(help_text=_("语义检查执行信息列表"), child=SemanticInfoSerializer())

    class Meta:
        swagger_schema_fields = {"example": mock_data.USER_SEMANTIC_LIST_REQUEST_DATA}


class DeleteUserSemanticListSerializer(serializers.Serializer):
    # user = serializers.CharField(help_text=_("用户名"))
    task_ids = serializers.ListField(help_text=_("语义执行的root id列表"), child=serializers.CharField())

    class Meta:
        swagger_schema_fields = {"example": mock_data.DELETE_USER_SEMANTIC_LIST_REQUEST_DATA}


class RevokeSemanticCheckSerializer(serializers.Serializer):
    root_id = serializers.CharField(help_text=_("流程id"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.REVOKE_SEMANTIC_CHECK_REQUEST_DATA}


class RevokeSemanticCheckResponseSerializer(serializers.Serializer):
    result = serializers.BooleanField(help_text=_("是否撤销成功"))
    message = serializers.CharField(help_text=_("撤销相关信息"))
    data = serializers.CharField(help_text=_("撤销相关数据"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.REVOKE_SEMANTIC_CHECK_RESPONSE_DATA}


class QuerySemanticDataSerializer(serializers.Serializer):
    root_id = serializers.CharField(help_text=_("流程id"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.REVOKE_SEMANTIC_CHECK_REQUEST_DATA}


class QuerySemanticDataResponseSerializer(serializers.Serializer):
    semantic_data = serializers.DictField(help_text=_("语义执行数据"))
    import_mode = serializers.ChoiceField(help_text=_("sql导入模式"), choices=SQLImportMode.get_choices())
    sql_data_ready = serializers.BooleanField(help_text=_("sql数据是否成功录入到pipeline"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.SEMANTIC_SQL_FILES}
