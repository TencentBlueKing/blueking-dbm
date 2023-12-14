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
from typing import Callable, Dict

from backend.bk_web.pagination import AuditedLimitOffsetPagination

from .query import ResourceList


class ResourceLimitOffsetPagination(AuditedLimitOffsetPagination):
    """专为 ResourceViewSet 定制的 LimitOffsetPagination, 用于处理 ResourceList 类型数据的分页问题"""

    no_limit_query_param = "no_limit"
    limit = 10
    offset = 0
    count = 0

    def paginate_list(self, request, bk_biz_id: int, query_method: Callable, query_params: Dict):

        # 支持返回全部数据：/list/?limit=-1
        if request.query_params.get(self.limit_query_param) == "-1":
            self.limit = -1
        else:
            self.limit = self.get_limit(request)

        # 支持返回全部数据（保留以前的协议）：/list/?no_limit=1
        if request.query_params.get(self.no_limit_query_param):
            self.limit = -1

        self.offset = self.get_offset(request)

        data_list: ResourceList = query_method(
            bk_biz_id,
            query_params=query_params,
            limit=self.limit,
            offset=self.offset,
        )

        self.request = request
        self.count = data_list.count

        if self.count > self.limit and self.template is not None:
            self.display_page_controls = True

        if self.count == 0 or self.offset > self.count:
            return []

        return data_list.data
