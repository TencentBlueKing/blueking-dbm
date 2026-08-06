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
from iam.resource.provider import ListResult, ResourceProvider

from backend.configuration.constants import DBType
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta

# 通用配置不属于任何真实 DB 类型，作为 dbtype 资源的一个特殊实例存在
COMMON_DB_TYPE = "common"


class DBTypeResourceProvider(ResourceProvider):
    """
    DBType资源是固定的，视图简化处理: 没有属性，全量返回资源
    """

    resource_meta: ResourceMeta = ResourceEnum.DBTYPE

    @staticmethod
    def get_display_name(db_type):
        if db_type == COMMON_DB_TYPE:
            return _("通用")
        return DBType.get_choice_label(db_type)

    def list_attr(self, **options):
        return ListResult(results=[], count=0)

    def list_attr_value(self, filter, page, **options):
        return ListResult(results=[], count=0)

    @staticmethod
    def filter_and_paginate(instances, filter, page) -> ListResult:
        """枚举资源的通用处理：按关键字过滤展示名，再分页。IAM要求默认支持 display_name 包含搜索"""
        keyword = filter.get("search") or filter.get("keyword")
        if keyword:
            instances = [instance for instance in instances if keyword in instance["display_name"]]
        return ListResult(results=instances[page.slice_from : page.slice_to], count=len(instances))

    def list_instance(self, filter, page, **options):
        db_types = [{"id": db.value, "display_name": DBType.get_choice_label(db.value)} for db in DBType]
        # 追加通用配置的特殊实例，用于通用配置的 dbconfig_edit 鉴权
        db_types.append({"id": COMMON_DB_TYPE, "display_name": self.get_display_name(COMMON_DB_TYPE)})
        return self.filter_and_paginate(db_types, filter, page)

    def search_instance(self, filter, page, **options):
        return self.list_instance(filter, page, **options)

    def list_instance_by_policy(self, filter, page, **options):
        return self.list_instance(filter, page, **options)

    def fetch_instance_info(self, filter, **options):
        items = [{"id": id, "display_name": self.get_display_name(id)} for id in filter.ids]
        return ListResult(results=items, count=len(items))
