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
from typing import Any, Dict, List

from blueapps.account.models import User
from django.db import models
from iam import PathEqDjangoQuerySetConverter
from iam.resource.provider import ListResult, ResourceProvider
from iam.resource.utils import FancyDict, Page

from backend.components.base import DataAPI
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.handlers.converter import InterfaceConverter


class CommonProviderMixin(object):
    """
    封装了Provider通用的，非ResourceProvider框架的方法
    """

    resource_meta: ResourceMeta = None

    @staticmethod
    def list_user_resource():
        """获取以user为属性的value"""
        users = User.objects.all()
        user_resource = [{"id": user.username, "display_name": user.username} for user in users]
        return user_resource

    @staticmethod
    def resources_filter(filter, resources) -> List[Dict]:
        """根据filter字段过滤resource"""
        if not filter.get("keyword") and not filter.get("ids"):
            return resources
        results = []
        for resource in resources:
            if filter.get("ids") and resource["id"] in filter.get("ids"):
                results.append(resource)
            if filter.get("keyword") and filter.get("keyword") in resource["display_name"]:
                results.append(resource)
        return results

    def fetch_instance_info_with_resource(self, id__bk_iam_path, resource_meta, resources, value_list) -> List[Dict]:
        """根据资源列表和字段，返回iam的资源字段信息"""
        results = []
        for item in resources:
            item["id"] = item.pop(resource_meta.lookup_field)
            if "display_name" in value_list:
                display_name_list = [str(item.pop(field, "")) for field in resource_meta.display_fields]
                item["display_name"] = ":".join(display_name_list) or item["id"]
            if "_bk_iam_path_" in value_list:
                item["_bk_iam_path_"] = id__bk_iam_path[item["id"]]
            results.append(item)

        return results


class BaseResourceProvider(ResourceProvider, CommonProviderMixin, metaclass=abc.ABCMeta):
    """
    基类Provider, 提供通用处理函数
    """

    resource_meta: ResourceMeta = None

    @abc.abstractmethod
    def get_bk_iam_path(self, instance_ids, *args, **kwargs) -> Dict:
        """获取实例的bk_iam_path，由各个视图独立实现"""
        raise NotImplementedError

    def _list_attr(self, id: str, display_name: str, **options) -> ListResult:
        """考虑只支持一种属性"""
        results = [{"id": id, "display_name": display_name}]
        return ListResult(results=results, count=len(results))

    def _list_attr_value(
        self, attr: str, resources: List[Dict], filter: FancyDict, page: Page, **options
    ) -> ListResult:
        """根据属性value过滤资源"""
        if filter.attr == attr:
            results = super().resources_filter(filter, resources)
            return ListResult(results=results[page.slice_from : page.slice_to], count=len(results))
        else:
            return ListResult(results=[], count=0)

    @abc.abstractmethod
    def _search_instance(self, data_source: Any, condition: Dict, value_list: List[str], page):
        """根据过滤条件搜索资源，由子类独立实现"""
        raise NotImplementedError

    @abc.abstractmethod
    def _list_instance(self, data_source: Any, condition: Dict, value_list: List[str], page: Page):
        """根据条件过滤资源列表，由子类独立实现"""
        raise NotImplementedError

    @abc.abstractmethod
    def _fetch_instance_info(
        self, data_source: Any, resource_meta: ResourceMeta, value_list: List[str], filter: FancyDict
    ):
        """批量获取资源实例详情，由子类独立实现"""
        raise NotImplementedError

    @abc.abstractmethod
    def _list_instance_by_policy(
        self,
        data_source: Any,
        value_list: List[str],
        key_mapping: Dict,
        value_hooks: Dict,
        filter: FancyDict,
        page: Page,
        **options,
    ):
        """根据策略获取资源，由子类独立实现"""
        raise NotImplementedError

    def list_attr(self, **options):
        """
        通过属性配置权限会用到, 没有属性权限管控不需要实现
        属性列表
        """
        return self._list_attr(id=self.resource_meta.attribute, display_name=self.resource_meta.attribute_display)

    def list_attr_value(self, filter, page, **options):
        """
        通过属性配置权限会用到, 没有属性权限管控不需要实现。默认实现是以"创建者"为属性
        属性值列表
        注意, 有翻页; 需要返回count
        """
        user_resource = super().list_user_resource()
        return self._list_attr_value(self.resource_meta.attribute, user_resource, filter, page, **options)

    def list_instance(self, filter, page, **options):
        """
        根据过滤条件查询实例
        """
        conditions = filter.get("conditions") or {}
        # 优先以祖先的拓扑层级过滤，其次考虑直接父级的过滤
        filter.ancestors = filter.get("ancestors") or [filter.get("parent")] or []
        ancestors_filter = {
            ResourceEnum.get_resource_by_id(parent["type"]).lookup_field: parent["id"]
            for parent in filter.ancestors
            if parent
        }
        conditions.update(ancestors_filter)
        # iam页面过滤搜索
        keyword = filter.get("search") or filter.get("keyword")
        if keyword:
            conditions.update({f"{filter.keyword_field}": keyword})

        return self._list_instance(
            data_source=filter.data_source, condition=conditions, value_list=filter.value_list, page=page
        )

    def search_instance(self, filter, page, **options):
        """
        实例搜索的时候会用到
        """
        return self.list_instance(filter, page, **options)

    def list_instance_by_policy(self, filter, page, **options):
        """
        动态查询资源实例进行预览，默认无实现
        """
        return ListResult(results=[], count=0)

    def fetch_instance_info(self, filter, **options):
        """
        批量获取资源实例详情
        """
        value_list = filter.get("attrs") or [self.resource_meta.attribute, "display_name", "_bk_iam_path_"]
        return self._fetch_instance_info(
            data_source=filter.data_source, resource_meta=self.resource_meta, value_list=value_list, filter=filter
        )


class BaseModelResourceProvider(BaseResourceProvider):
    """
    模型基类Provider, 提供通用处理函数。
    适用于资源是在DBM服务内，可以通过ORM查询
    """

    resource_meta: ResourceMeta = None
    model: models.Model = None

    def get_model_bk_iam_path(self, model, instance_ids, *args, **kwargs) -> Dict:
        """获取带有模型实例的bk_iam_path"""
        instances = model.objects.filter(pk__in=instance_ids)
        # 默认考虑一层父类
        id__bk_iam_path = {
            instance.id: "/{},{}/".format(
                self.resource_meta.parent.id,
                getattr(instance, self.resource_meta.parent.lookup_field),
            )
            for instance in instances
        }
        return id__bk_iam_path

    def get_bk_iam_path(self, instance_ids, *args, **kwargs) -> Dict:
        return self.get_model_bk_iam_path(self.model, instance_ids, *args, **kwargs)

    def _search_instance(self, data_source: models.Model, condition: Dict, value_list: List[str], page):
        return self._list_instance(data_source, condition, value_list, page)

    def _list_instance(self, data_source: models.Model, condition: Dict, value_list: List[str], page):
        # 根据过滤条件查询关联的queryset
        queryset = data_source.objects.filter(**condition).values(*value_list)[page.slice_from : page.slice_to]
        results = [
            {"id": str(item[value_list[0]]), "display_name": "-".join([str(item[value]) for value in value_list[1:]])}
            for item in list(queryset)
        ]
        return ListResult(results=results, count=len(results))

    def _fetch_instance_info(
        self, data_source: models.Model, resource_meta: ResourceMeta, value_list: List[str], filter
    ):
        # 查询关联字段的queryset
        field_list = [field for field in value_list if field not in ["_bk_iam_path_", "display_name"]]
        field_list.extend([resource_meta.lookup_field, *resource_meta.display_fields])
        queryset = data_source.objects.filter(pk__in=filter.ids).values(*field_list)
        # 获取资源实例与_bk_iam_path_的关联
        id__bk_iam_path = self.get_bk_iam_path(filter.ids)
        # 根据value_list，获取实例信息字段
        results = self.fetch_instance_info_with_resource(id__bk_iam_path, resource_meta, queryset, value_list)
        return ListResult(results=results, count=len(results))

    def _list_instance_by_policy(
        self,
        data_source: models.Model,
        value_list: List[str],
        key_mapping: Dict,
        value_hooks: Dict,
        filter: FancyDict,
        page: Page,
        **options,
    ):
        expression = filter.expression
        # 无策略表达式，则直接返回
        if not expression:
            return ListResult(results=[], count=0)

        # 根据转换钩子将表达式转换为orm的过滤条件
        converter = options.get("converter_class", PathEqDjangoQuerySetConverter)(key_mapping, value_hooks)
        filters = converter.convert(expression)

        # 过滤资源实例
        queryset = data_source.objects.filter(filters).values(*value_list)[page.slice_from : page.slice_to]
        results = [
            {"id": str(item[value_list[0]]), "display_name": ":".join([str(item[value]) for value in value_list[1:]])}
            for item in queryset
        ]

        return ListResult(results=results, count=len(results))


class BaseInterfaceResourceProvider(BaseResourceProvider):
    """
    接口基类Provider, 提供通用处理函数。
    适用于资源是在DBM服务外部，可以通过接口查询
    """

    resource_meta: ResourceMeta = None
    # 获取资源数据的api，默认需要支持分页
    api: DataAPI = None

    def get_bk_iam_path(self, instance_ids, *args, **kwargs) -> Dict:
        instances = self.api(params={"ids": instance_ids})["results"]
        # 默认考虑一层父类
        id__bk_iam_path = {
            instance["id"]: "/{},{}/".format(
                self.resource_meta.parent.id, instance[self.resource_meta.parent.lookup_field]
            )
            for instance in instances
        }
        return id__bk_iam_path

    @staticmethod
    def convert_condition_field(condition: Dict):
        """转换过滤字段: 模糊字段(xx__contains)，主键(id)，主键数组(ids)等。子类可覆写"""
        return condition

    def _search_instance(self, data_source: DataAPI, condition: Dict, value_list: List[str], page: Page):
        return self._list_instance(data_source, condition, value_list, page)

    def _list_instance(self, data_source: DataAPI, condition: Dict, value_list: List[str], page: Page):
        # 转换查询字段(需要api接口支持)
        condition = self.convert_condition_field(condition)
        # 填充分页参数
        condition.update(limit=page.limit, offset=page.offset)
        # 查询数据
        data = data_source(params=condition)["results"]
        results = [
            {"id": str(item[value_list[0]]), "display_name": ":".join([str(item[value]) for value in value_list[1:]])}
            for item in list(data)
        ]
        return ListResult(results=results, count=len(results))

    def _fetch_instance_info(
        self, data_source: DataAPI, resource_meta: ResourceMeta, value_list: List[str], filter: FancyDict
    ):
        # 查询关联字段的queryset
        field_list = [field for field in value_list if field not in ["_bk_iam_path_", "display_name"]]
        field_list.extend([resource_meta.lookup_field, *resource_meta.display_fields])
        data = [{field: d[field] for field in field_list} for d in data_source(params={"ids": filter.ids})["results"]]
        # 获取资源实例与_bk_iam_path_的关联
        id__bk_iam_path = self.get_bk_iam_path(filter.ids)
        # 根据value_list，获取实例信息字段
        results = self.fetch_instance_info_with_resource(id__bk_iam_path, resource_meta, data, value_list)
        return ListResult(results=results, count=len(results))

    def _list_instance_by_policy(
        self,
        data_source: DataAPI,
        value_list: List[str],
        key_mapping: Dict,
        value_hooks: Dict,
        filter: FancyDict,
        page: Page,
        **options,
    ):
        expression = filter.expression
        # 无策略表达式，则直接返回
        if not expression:
            return ListResult(results=[], count=0)

        # 根据转换钩子将表达式转换为orm的过滤条件
        converter = options.get("converter_class", InterfaceConverter)(key_mapping, value_hooks)
        filters = converter.convert(expression)

        # 过滤资源实例
        filters.update(limit=page.limit, offset=page.offset)
        data = [{field: d[field] for field in value_list} for d in data_source(params=filters)["results"]]
        results = [
            {"id": str(item[value_list[0]]), "display_name": ":".join([str(item[value]) for value in value_list[1:]])}
            for item in data
        ]

        return ListResult(results=results, count=len(results))
