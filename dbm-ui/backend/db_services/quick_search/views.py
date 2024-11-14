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
from hashlib import md5

from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.quick_search.handlers import QSearchHandler
from backend.db_services.quick_search.serializers import QuickSearchSerializer

logger = logging.getLogger("root")
SWAGGER_TAG = [_("全局搜索")]


class QuickSearchViewSet(viewsets.SystemViewSet):
    default_permission_class = []
    serializer_class = QuickSearchSerializer

    @common_swagger_auto_schema(
        operation_summary=_("[quick_search] 快速查询"),
        request_body=QuickSearchSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=QuickSearchSerializer)
    def search(self, request, *args, **kwargs):
        params = self.params_validate(self.get_serializer_class())
        keyword = params.pop("keyword", "")
        short_code = params.pop("short_code", "")
        # 优先使用短码
        if short_code:
            keyword = cache.get(f"shot_code_{short_code}")
        else:
            short_code = md5(keyword.encode("utf-8")).hexdigest()
            cache.set(f"shot_code_{short_code}", keyword, 60 * 60 * 24)

        result = QSearchHandler(**params).search(keyword)
        result.update({"short_code": short_code, "keyword": keyword})
        return Response(result)
