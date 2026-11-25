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

from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.dbm_aiagent.mcp_tools.hdfs.impl.hdfs_toolbox import (
    DB_COUNT_MAX,
    NAMED_TABLE_MAX,
    TABLE_COUNT_MAX,
    TASK_STATUS_CHOICES,
    TOOLBOX_TASKS,
    validate_iceberg_db_dir,
    validate_iceberg_table_dir,
)


class HdfsToolboxBaseInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名(immute_domain)"))


class HdfsListIcebergTablesInputSerializer(HdfsToolboxBaseInputSerializer):
    db_dir = serializers.CharField(help_text=_("库目录，形如 /data/iceberg/warehouse/<库目录>"))

    def validate_db_dir(self, value):
        return _validate(validate_iceberg_db_dir, value)


class HdfsGetIcebergTableSizesInputSerializer(HdfsToolboxBaseInputSerializer):
    table_dirs = serializers.ListField(
        child=serializers.CharField(),
        min_length=1,
        max_length=NAMED_TABLE_MAX,
        help_text=format_lazy(_("表目录，形如 /data/iceberg/warehouse/<库目录>/<表目录>，最多 {} 个"), NAMED_TABLE_MAX),
    )

    def validate_table_dirs(self, value):
        return [_validate(validate_iceberg_table_dir, path) for path in value]


class HdfsToolboxSubmitOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    task_type = serializers.ChoiceField(choices=list(TOOLBOX_TASKS), help_text=_("任务类型"))
    job_instance_id = serializers.IntegerField(help_text=_("作业实例 ID，用于 hdfs_toolbox_query_result 查询结果"))
    poll_interval_seconds = serializers.IntegerField(help_text=_("建议的查询间隔，秒"))
    message = serializers.CharField(help_text=_("下一步操作说明"))


class HdfsToolboxQueryResultInputSerializer(HdfsToolboxBaseInputSerializer):
    job_instance_id = serializers.IntegerField(help_text=_("提交工具返回的作业实例 ID"))


class HdfsToolboxQueryResultOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    job_instance_id = serializers.IntegerField(help_text=_("作业实例 ID"))
    task_type = serializers.ChoiceField(choices=list(TOOLBOX_TASKS), help_text=_("任务类型"))
    status = serializers.ChoiceField(
        choices=list(TASK_STATUS_CHOICES),
        help_text=_("running 表示执行中，需稍后再查；succeeded 表示成功，结果在 result；failed 表示失败，原因在 message"),
    )
    elapsed_seconds = serializers.IntegerField(help_text=_("距提交已过去的秒数"))
    message = serializers.CharField(help_text=_("执行中或失败时的说明"), allow_blank=True)
    result = serializers.JSONField(
        allow_null=True,
        help_text=format_lazy(
            _(
                "status=succeeded 时的结果，其余为 null。按 task_type 区分："
                "list_iceberg_dbs 为 {{warehouse_dir, db_count, truncated, message, db_dirs}}，"
                "db_dirs 最多 {} 个；"
                "list_iceberg_tables 为 {{db_dir, table_count, truncated, message, table_dirs}}，"
                "table_dirs 最多 {} 个；"
                "get_iceberg_table_sizes 为 {{table_count, tables, failed_count, failed_tables}}，"
                "tables 为 du 成功的表目录，按传入顺序，每项含 "
                "path、name、db_dir、logical_bytes（逻辑大小）、disk_bytes（含副本磁盘占用）、"
                "logical_human、disk_human；failed_tables 为 du 失败的表目录，每项含 path、error，"
                "单张表失败不影响其余表"
            ),
            DB_COUNT_MAX,
            TABLE_COUNT_MAX,
        ),
    )


def _validate(validator, value: str) -> str:
    try:
        return validator(value)
    except ValueError as exc:
        raise serializers.ValidationError(str(exc))
