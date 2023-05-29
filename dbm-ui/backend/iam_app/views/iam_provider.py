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

import abc
from typing import Dict, List

from django.db import models
from iam import PathEqDjangoQuerySetConverter
from iam.resource.provider import ListResult, ResourceProvider


class BaseResourceProvider(ResourceProvider, metaclass=abc.ABCMeta):
    """
    基类Provider, 提供通用处理函数
    """

    def resources_filter(self, filter: Dict, resources: List[Dict]) -> List[Dict]:
        if not filter.get("keyword") and not filter.get("ids"):
            return resources

        results = []
        for resource in resources:
            if resource["id"] in filter.get("ids") or filter.get("keyword") in resource["display_name"]:
                results.append(resource)

        return results

    def _list_attr(self, id: str, display_name: str, **options) -> ListResult:
        results = [{"id": id, "display_name": display_name}]
        return ListResult(results=results, count=len(results))

    def _list_attr_value(self, attr: str, resources: List[Dict], filter, page, **options) -> ListResult:
        if filter.get("attr") == attr:
            results = self.resources_filter(filter, resources)
            return ListResult(results=results[page.slice_from : page.slice_to], count=len(results))
        else:
            return ListResult(results=[], count=0)

    def _search_instance(
        self, obj_model: models.Model, condition: Dict, value_list: List[str], filter, page, **options
    ):
        queryset = obj_model.objects.filter(**condition).values(*value_list)[page.slice_from : page.slice_to]
        results = [
            {"id": str(item[value_list[0]]), "display_name": str(item[value_list[1]])} for item in list(queryset)
        ]
        return ListResult(results=results, count=len(results))

    def _list_instance(self, filter, page, **options):
        """
        TODO 由于每个模型的层级不同，因此不好抽象为统一方法，暂搁置
        """
        pass

    def _fetch_instance_info(self, obj_model: models.Model, value_list: List[str], filter, **options):
        """
        暂时不考虑属性的过滤
        """

        ids = []
        if filter.ids:
            # TODO 默认认为主键是int类型，后面可能考虑动态转换类型
            ids = [int(i) for i in filter.ids]

        queryset = obj_model.objects.filter(pk__in=ids).values(*value_list)

        results = [{"id": str(item[value_list[0]]), "display_name": str(item[value_list[1]])} for item in queryset]
        return ListResult(results=results, count=len(results))

    def _list_instance_by_policy(
        self,
        obj_model: models.Model,
        value_list: List[str],
        key_mapping: Dict,
        value_hooks: str,
        filter,
        page,
        **options
    ):
        expression = filter.expression
        if not expression:
            return ListResult(results=[], count=0)

        converter = PathEqDjangoQuerySetConverter(key_mapping, {value_hooks: lambda value: value[1:-1].split(",")[1]})
        filters = converter.convert(expression)
        queryset = obj_model.objects.filter(filters).values(*value_list)[page.slice_from : page.slice_to]
        results = [{"id": str(item[value_list[0]]), "display_name": str(item[value_list[1]])} for item in queryset]
        return ListResult(results=results, count=len(results))

    def list_attr(self, **options):
        """通过属性配置权限会用到, 没有属性权限管控不需要实现
        属性列表
        """
        return ListResult(results=[], count=0)

    def list_attr_value(self, filter, page, **options):
        """通过属性配置权限会用到, 没有属性权限管控不需要实现
        属性值列表
        注意, 有翻页; 需要返回count
        """
        return ListResult(results=[], count=0)

    def search_instance(self, filter, page, **options):
        """
        实例搜索的时候会用到
        """
        return ListResult(results=[], count=0)

    def list_instance_by_policy(self, filter, page, **options):
        """
        动态查询资源实例进行预览
        """
        return ListResult(results=[], count=0)


class BusinessResourceProvider(BaseResourceProvider):
    """
    业务资源相关的Provider
    注: 这里设计为从cmdb拉取资源，因此不用设计business的Provider了
    """

    pass
