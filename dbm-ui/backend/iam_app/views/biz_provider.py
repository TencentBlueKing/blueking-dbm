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

from collections import defaultdict
from typing import Dict, List

from django.db import models
from django.utils.translation import gettext_lazy as _
from iam.resource.provider import ListResult

from backend.db_meta.models import AppCache
from backend.iam_app.constans import GLOBAL_BIZ_ID_V4
from backend.iam_app.dataclass.resources import DBMBizResourceMeta, ResourceEnum
from backend.iam_app.views.iam_provider import BaseModelResourceProvider


class BusinessResourceProvider(BaseModelResourceProvider):
    """
    业务资源的反向拉取类。

    V4不支持跨系统资源，业务不再引用cmdb而是挂在dbm系统下，数据源为本地的业务缓存。
    """

    model: models.Model = AppCache
    resource_meta: DBMBizResourceMeta = ResourceEnum.DBMBIZ

    @staticmethod
    def get_global_biz() -> Dict:
        """平台级资源没有真实业务，统一挂在虚拟业务下，该实例不在业务缓存中"""
        return {"id": str(GLOBAL_BIZ_ID_V4), "display_name": str(_("全局"))}

    def get_bk_iam_path(self, instance_ids, *args, **kwargs) -> Dict:
        # 业务是顶层资源没有上级拓扑，用defaultdict避免调用方按实例ID取值时的类型差异
        return defaultdict(str)

    def list_instance(self, filter, page, **options):
        filter.data_source = self.model
        filter.value_list = [self.resource_meta.lookup_field, *self.resource_meta.display_fields]
        filter.keyword_field = "bk_biz_name__icontains"
        result = super().list_instance(filter, page, **options)

        # 虚拟业务不在数据源里，仅在首页追加
        global_biz = self.get_global_biz()
        keyword = filter.get("search") or filter.get("keyword")
        if page.offset == 0 and (not keyword or keyword in global_biz["display_name"]):
            result.results.insert(0, global_biz)
            result.count += 1
        return result

    def fetch_instance_info(self, filter, **options):
        filter.data_source = self.model
        global_biz = self.get_global_biz()
        biz_ids: List = [str(biz_id) for biz_id in (filter.ids or [])]

        results = []
        filter.ids = [biz_id for biz_id in biz_ids if biz_id != global_biz["id"]]
        if filter.ids:
            results = super().fetch_instance_info(filter, **options).results
        if global_biz["id"] in biz_ids:
            results.insert(0, global_biz)

        return ListResult(results=results, count=len(results))
