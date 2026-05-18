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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class MongoExecuteTcpCmdSerializer(serializers.Serializer):
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())

    class Meta:
        swagger_schema_fields = {"example": {"job_instance_id": 0, "job_instance_name": "xxxx"}}


class GetMongoTcpResultSerializer(serializers.Serializer):
    job_instance_id = serializers.IntegerField(help_text=_("job实例ID"))


class GetMongoShardSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=False)
    shard_names = serializers.CharField(help_text=_("业务ID"), required=False)

    def validate(self, attrs):
        if attrs.get("shard_names"):
            attrs["shard_names"] = attrs["shard_names"].split(",")
        return attrs


class ListAvailableVersionSerializer(serializers.Serializer):
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField(), allow_empty=False)


class MongoScriptSyntaxCheckSerializer(serializers.Serializer):
    """MongoDB脚本语法检查序列化器"""

    script_content = serializers.CharField(help_text=_("脚本内容列表"), required=False)
    script_files = serializers.ListField(
        help_text=_("脚本文件列表"), child=serializers.FileField(help_text=_("脚本文件"), required=False), required=False
    )

    def validate(self, attrs):
        from backend.db_services.mongodb.toolbox.constants import MAX_UPLOAD_SCRIPT_FILE_SIZE, SCRIPT_FILE_EXTENSIONS

        script_contents = attrs.get("script_content", [])
        script_files = attrs.get("script_files", [])
        script_filenames = attrs.get("script_filenames", [])

        if not (script_contents or script_files or script_filenames):
            raise serializers.ValidationError(_("脚本内容不能为空！"))

        # 验证文件扩展名和大小 - 收集所有错误后一次性返回
        errors = []
        for file in script_files:
            # 验证文件扩展名
            if not any(file.name.lower().endswith(ext) for ext in SCRIPT_FILE_EXTENSIONS):
                errors.append(_("请保证脚本文件[{}]的后缀为{}").format(file.name, ", ".join(SCRIPT_FILE_EXTENSIONS)))

            # 验证文件大小
            if file.size > MAX_UPLOAD_SCRIPT_FILE_SIZE:
                errors.append(_("请保证单个文件{}不超过1G").format(file.name))

        # 如果有错误，一次性抛出所有错误信息
        if errors:
            raise serializers.ValidationError(" ".join(errors))

        return attrs


class MongoScriptSyntaxCheckResponseSerializer(serializers.Serializer):
    """MongoDB脚本语法检查响应序列化器"""

    scripts = serializers.ListField(help_text=_("脚本文件信息列表"), child=serializers.DictField(), required=True)

    class Meta:
        swagger_schema_fields = {
            "example": [
                {
                    "script_path": "mongodb/scripts/{biz}/test.js",
                    "script_content": "db.test.find()",
                    "raw_file_name": "test.js",
                }
            ],
            "example_multiple": [
                {
                    "script_path": "mongodb/scripts/{biz}/test1.js",
                    "script_content": "db.test.find()",
                    "raw_file_name": "test1.js",
                },
                {
                    "script_path": "mongodb/scripts/{biz}/test2.js",
                    "script_content": "db.test2.find()",
                    "raw_file_name": "test2.js",
                },
            ],
        }
