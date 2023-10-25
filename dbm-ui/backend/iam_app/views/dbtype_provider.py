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

from iam.resource.provider import ListResult, ResourceProvider

from backend.configuration.constants import DBType
from backend.iam_app.dataclass.resources import ResourceMeta


class DBTypeResourceProvider(ResourceProvider):
    """
    DBType资源是固定的，视图简化处理: 没有属性，全量返回资源
    """

    resource_meta: ResourceMeta = None

    def list_attr(self, **options):
        return ListResult(results=[], count=0)

    def list_attr_value(self, filter, page, **options):
        return ListResult(results=[], count=0)

    def list_instance(self, filter, page, **options):
        db_types = [{"id": db.value, "display_name": db.name} for db in DBType]
        return ListResult(results=db_types, count=len(db_types))

    def search_instance(self, filter, page, **options):
        return self.list_instance(filter, page, **options)

    def list_instance_by_policy(self, filter, page, **options):
        return self.list_instance(filter, page, **options)

    def fetch_instance_info(self, filter, **options):
        items = [{"id": id, "display_name": DBType.get_choice_label(id)} for id in filter.ids]
        return ListResult(results=items, count=len(items))
