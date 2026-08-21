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

from typing import Dict, List

from iam.resource.provider import ListResult, ResourceProvider

from backend.configuration.constants import DBType
from backend.db_meta.models import AppCache
from backend.iam_app.constans import COMMON_DB_TYPE
from backend.iam_app.dataclass.resources import BizDBTypeResourceMeta, BusinessResourceMeta, ResourceEnum


def get_biz_names() -> Dict[str, str]:
    bizs = AppCache.get_appcache(key="appcache_dict")
    return {str(bk_biz_id): biz["bk_biz_name"] for bk_biz_id, biz in bizs.items()}


class BizDBTypeResourceProvider(ResourceProvider):
    """
    业务DB类型资源的反向拉取类。

    实例为「业务 × DB类型」的组合，ID格式 {业务ID}-{DB类型}。
    DB类型除了真实的DB外，还包含一个通用(common)兜底实例
    """

    resource_meta: BizDBTypeResourceMeta = ResourceEnum.BIZ_DBTYPE

    @staticmethod
    def get_db_types() -> List[str]:
        return [db.value for db in DBType] + [COMMON_DB_TYPE]

    @staticmethod
    def get_db_type_name(db_type: str) -> str:
        return str(ResourceEnum.DBTYPE.get_display_name(db_type) or db_type)

    def make_instance(self, bk_biz_id, biz_name: str, db_type: str) -> Dict:
        return {
            "id": self.resource_meta.make_instance_id(bk_biz_id, db_type),
            "display_name": "{}-{}".format(biz_name, self.get_db_type_name(db_type)),
        }

    def list_attr(self, **options):
        return ListResult(results=[], count=0)

    def list_attr_value(self, filter, page, **options):
        return ListResult(results=[], count=0)

    def list_instance(self, filter, page, **options):
        biz_names = get_biz_names()
        # IAM按业务逐层选择实例时会带上直接上级，此时只展开该业务下的DB类型
        parent = filter.get("parent") or {}
        if parent.get("type") == BusinessResourceMeta.id and parent.get("id"):
            bk_biz_id = str(parent["id"])
            biz_names = {bk_biz_id: biz_names.get(bk_biz_id, bk_biz_id)}

        instances = [
            self.make_instance(bk_biz_id, biz_name, db_type)
            for bk_biz_id, biz_name in biz_names.items()
            for db_type in self.get_db_types()
        ]
        keyword = filter.get("search") or filter.get("keyword")
        if keyword:
            instances = [instance for instance in instances if keyword in instance["display_name"]]
        return ListResult(results=instances[page.slice_from : page.slice_to], count=len(instances))

    def search_instance(self, filter, page, **options):
        return self.list_instance(filter, page, **options)

    def list_instance_by_policy(self, filter, page, **options):
        return ListResult(results=[], count=0)

    def fetch_instance_info(self, filter, **options):
        biz_names = get_biz_names()
        results = []
        for instance_id in filter.ids or []:
            bk_biz_id, db_type = self.resource_meta.parse_instance_id(instance_id)
            biz_name = biz_names.get(bk_biz_id, bk_biz_id)
            results.append(
                {
                    "id": instance_id,
                    "display_name": "{}-{}".format(biz_name, self.get_db_type_name(db_type)),
                    "_bk_iam_path_": "/{},{}/".format(BusinessResourceMeta.id, bk_biz_id),
                }
            )
        return ListResult(results=results, count=len(results))
