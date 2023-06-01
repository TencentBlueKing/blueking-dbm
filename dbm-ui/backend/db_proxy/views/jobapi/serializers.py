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

from backend.constants import DATETIME_PATTERN
from backend.db_proxy.views import mock_data
from backend.db_proxy.views.serialiers import BaseProxyPassSerialier


class ServerItemSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"), required=True)
    ip = serializers.IPAddressField(help_text=_("主机ip"), required=True)


class FastExecuteScriptSerializer(BaseProxyPassSerialier):
    bk_cloud_id = serializers.IntegerField()
    ip_list = serializers.ListField(help_text=_("执行脚本的主机ip列表"), child=ServerItemSerializer(), required=True)
    script_content = serializers.CharField(help_text=_("脚本内容"), required=True)
    script_language = serializers.IntegerField(help_text=_("脚本语言类型"), required=True)
    account = serializers.CharField(help_text=_("执行脚本的账号"), required=True)
    timeout = serializers.IntegerField(help_text=_("超时时间,单位秒"), required=True)


class FastExecuteScriptResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.JOB_API_FAST_EXECUTE_SCRIPT_DATA_RESPONSE}


class JobInstanceStatusSerializer(BaseProxyPassSerialier):
    job_instance_id = serializers.IntegerField(help_text=_("任务实例ID"), required=True)


class GetJobInstanceStatusResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.JOB_API_GET_JOB_INSTANCE_STATUS_DATA_RESPONSE}


class GetJobInstanceIpLogSerializer(BaseProxyPassSerialier):
    bk_cloud_id = serializers.IntegerField()
    job_instance_id = serializers.IntegerField(help_text=_("任务实例ID"), required=True)
    step_instance_id = serializers.IntegerField(help_text=_("步骤实例ID"), required=True)
    ip_list = serializers.ListField(help_text=_("执行脚本的主机ip列表"), child=ServerItemSerializer(), required=True)


class GetJobInstanceIpLogResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.JOB_API_GET_JOB_INSTANCE_IP_LOG_DATA_RESPONSE}


class TransferFileSerializer(BaseProxyPassSerialier):
    class SourceFileItemSerializer(serializers.Serializer):
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"), required=True)
        ip = serializers.IPAddressField(help_text=_("源主机ip"), required=True)
        account = serializers.CharField(help_text=_("源主机账号"), required=True)
        file_list = serializers.ListField(
            help_text=_("文件列表"),
            child=serializers.CharField(help_text=_("文件路径")),
            required=True,
        )

    class TargetServerItemSerializer(serializers.Serializer):
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"), required=True)
        ip = serializers.IPAddressField(help_text=_("目标主机ip"), required=True)

    source_list = serializers.ListField(help_text=_("源文件列表"), child=SourceFileItemSerializer(), required=True)
    target_account = serializers.CharField(help_text=_("目标账号"), required=True)
    target_dir = serializers.CharField(help_text=_("目标目录"), required=True)
    target_ip_list = serializers.ListField(help_text=_("目标主机ip列表"), child=TargetServerItemSerializer(), required=True)
    timeout = serializers.IntegerField(help_text=_("超时时间,单位秒"), required=True)
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"), required=True)
    db_cloud_token = serializers.CharField(help_text=_("db_cloud_token"), required=True)


class TransferFileResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.TRANSFER_FILE_DATA_RESPONSE}
