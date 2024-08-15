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

from backend.core.storages import mock_data


class BatchDownloadFileSerializer(serializers.Serializer):
    file_path_list = serializers.ListField(help_text=_("文件路径列表"), child=serializers.CharField(), min_length=1)


class FileSerializer(serializers.Serializer):
    file_path = serializers.CharField(help_text=_("文件路径"))


class TemporaryDownloadSerializer(serializers.Serializer):
    token = serializers.CharField(help_text=_("临时下载的token"), required=False)
    download = serializers.BooleanField(help_text=_("是否强制下载"), required=False)


class CreateTokenSerializer(serializers.Serializer):
    file_path = serializers.CharField(help_text=_("文件路径"))

    class Meta:
        swagger_schema_fields = {"example": {"file_path": mock_data.CREATE_TOKEN_DATA["path"]}}


class CreateTokenSerializerResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.CREATE_TOKEN_DATA}


class DirDownloadSerializer(serializers.Serializer):
    paths = serializers.ListField(help_text=_("目标目录列表"), child=serializers.CharField(), min_length=1)
    force_download = serializers.BooleanField(help_text=_("是否下载"), required=False, default=True)
