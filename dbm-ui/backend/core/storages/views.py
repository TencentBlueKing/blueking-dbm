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
from django.utils.translation import ugettext as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.core.storages.handlers import StorageHandler
from backend.core.storages.serializers import BatchDownloadFileSerializer, FileSerializer

SWAGGER_TAG = "storage"


class StorageViewSet(viewsets.SystemViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("批量获取文件内容"), request_body=BatchDownloadFileSerializer(), tags=[SWAGGER_TAG]
    )
    @action(methods=["POST"], detail=False, serializer_class=BatchDownloadFileSerializer)
    def batch_fetch_file_content(self, request):
        file_path_list = self.params_validate(self.get_serializer_class())["file_path_list"]
        return Response(StorageHandler().batch_fetch_file_content(file_path_list=file_path_list))

    @common_swagger_auto_schema(operation_summary=_("获取文件内容"), query_serializer=FileSerializer(), tags=[SWAGGER_TAG])
    @action(methods=["GET"], detail=False, serializer_class=FileSerializer)
    def fetch_file_content(self, request):
        file_path = self.params_validate(self.get_serializer_class())["file_path"]
        return Response(StorageHandler().batch_fetch_file_content(file_path_list=[file_path])[0])

    @common_swagger_auto_schema(operation_summary=_("删除文件"), request_body=FileSerializer(), tags=[SWAGGER_TAG])
    @action(methods=["DELETE"], detail=False, serializer_class=FileSerializer)
    def delete_file(self, request):
        file_path = self.params_validate(self.get_serializer_class())["file_path"]
        return Response(StorageHandler().delete_file(file_path=file_path))
