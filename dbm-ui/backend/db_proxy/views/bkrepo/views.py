# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import os

from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.core.storages.storage import get_storage
from backend.db_proxy.constants import SWAGGER_TAG
from backend.db_proxy.views.bkrepo.serializers import UploadSerializer
from backend.db_proxy.views.views import BaseProxyPassViewSet


class BKRepoProxyPassViewSet(BaseProxyPassViewSet):
    """
    BKRepo接口的透传视图
    """

    @common_swagger_auto_schema(
        operation_summary=_("[bkrepo]上传文件"),
        request_body=UploadSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["PUT"],
        detail=False,
        serializer_class=UploadSerializer,
        url_path=r"generic/(?P<project>[\.\w-]+)/(?P<repo>[\.\w-]+)/(?P<path>[\./\w-]+)",
    )
    def upload_file(self, request, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        file = validated_data["file"]
        storage = get_storage(file_overwrite=False, bucket=kwargs["repo"])
        file_path = storage.save(name=os.path.join(kwargs["path"], file.name), content=file)
        return Response({"file_path": file_path})
