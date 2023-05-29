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

from rest_framework.pagination import LimitOffsetPagination


class AuditedLimitOffsetPagination(LimitOffsetPagination):
    def paginate_queryset(self, queryset, request, view=None):
        # 先运行父类paginate_queryset，初始化分页参数，获得原始数据
        page_data = super().paginate_queryset(queryset, request, view)

        # 如果limit参数为-1，则表示不分页
        try:
            if int(request.query_params[self.limit_query_param]) == -1:
                page_data = list(queryset)
        except (KeyError, ValueError):
            pass

        return page_data
