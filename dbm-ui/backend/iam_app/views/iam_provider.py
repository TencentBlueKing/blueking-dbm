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

from blueapps.account.models import User
from django.db import models
from iam import PathEqDjangoQuerySetConverter
from iam.resource.provider import ListResult, ResourceProvider

from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta


class CommonProviderMixin(object):
    """
    封装了Provider可能用到的方法
    """

    resource_meta: ResourceMeta = None

    def get_model_bk_iam_path(self, model, instance_ids, *args, **kwargs) -> Dict:
        """获取带有模型实例的bk_iam_path"""
        instances = model.objects.filter(pk__in=instance_ids)
        # 默认考虑一层父类
        id__bk_iam_path = {
            instance.id: "/{},{},{}/".format(
                self.resource_meta.parent.system_id,
                self.resource_meta.parent.id,
                getattr(instance, self.resource_meta.parent.lookup_field),
            )
            for instance in instances
        }
        return id__bk_iam_path

    @staticmethod
    def list_user_resource():
        """获取以user为属性的value"""
        users = User.objects.all()
        user_resource = [{"id": user.username, "display_name": user.username} for user in users]
        return user_resource


class BaseResourceProvider(ResourceProvider, metaclass=abc.ABCMeta):
    """
    基类Provider, 提供通用处理函数
    """

    resource_meta: ResourceMeta = None

    def resources_filter(self, filter, resources) -> List[Dict]:
        if not filter.get("keyword") and not filter.get("ids"):
            return resources

        results = []
        for resource in resources:
            if filter.get("ids") and resource["id"] in filter.get("ids"):
                results.append(resource)
            if filter.get("keyword") and filter.get("keyword") in resource["display_name"]:
                results.append(resource)

        return results

    def get_bk_iam_path(self, instance_ids, *args, **kwargs) -> Dict:
        """获取实例的bk_iam_path，由各个视图独立实现"""
        id__bk_iam_path = {inst: "" for inst in instance_ids}
        return id__bk_iam_path

    def _list_attr(self, id: str, display_name: str, **options) -> ListResult:
        """考虑只支持一种属性"""
        results = [{"id": id, "display_name": display_name}]
        return ListResult(results=results, count=len(results))

    def _list_attr_value(self, attr: str, resources: List[Dict], filter, page, **options) -> ListResult:
        if filter.attr == attr:
            results = self.resources_filter(filter, resources)
            return ListResult(results=results[page.slice_from : page.slice_to], count=len(results))
        else:
            return ListResult(results=[], count=0)

    def _search_instance(self, obj_model: models.Model, condition: Dict, value_list: List[str], page):
        return self._list_instance(obj_model, condition, value_list, page)

    def _list_instance(self, obj_model: models.Model, condition: Dict, value_list: List[str], page):
        queryset = obj_model.objects.filter(**condition).values(*value_list)[page.slice_from : page.slice_to]
        results = [
            {"id": str(item[value_list[0]]), "display_name": ":".join([str(item[value]) for value in value_list[1:]])}
            for item in list(queryset)
        ]
        return ListResult(results=results, count=len(results))

    def _fetch_instance_info(
        self, obj_model: models.Model, resource_meta: ResourceMeta, value_list: List[str], filter
    ):
        # 查询关联字段的queryset
        field_list = [field for field in value_list if field not in ["_bk_iam_path_", "display_name"]]
        field_list.extend([resource_meta.lookup_field, *resource_meta.display_fields])
        queryset = obj_model.objects.filter(pk__in=filter.ids).values(*field_list)
        # 获取资源实例与_bk_iam_path_的关联
        id__bk_iam_path = self.get_bk_iam_path(filter.ids)

        results = []
        for item in queryset:
            item["id"] = item.pop(resource_meta.lookup_field)
            if "display_name" in value_list:
                display_name_list = [str(item.pop(field, "")) for field in resource_meta.display_fields]
                item["display_name"] = ":".join(display_name_list) or item["id"]
            if "_bk_iam_path_" in value_list:
                item["_bk_iam_path_"] = id__bk_iam_path[item["id"]]

            results.append(item)

        return ListResult(results=results, count=len(results))

    def _list_instance_by_policy(
        self,
        obj_model: models.Model,
        value_list: List[str],
        key_mapping: Dict,
        value_hooks: Dict,
        filter,
        page,
        **options,
    ):
        expression = filter.expression
        if not expression:
            return ListResult(results=[], count=0)

        converter = options.get("converter_class", PathEqDjangoQuerySetConverter)(key_mapping, value_hooks)
        filters = converter.convert(expression)
        queryset = obj_model.objects.filter(filters).values(*value_list)[page.slice_from : page.slice_to]
        results = [
            {"id": str(item[value_list[0]]), "display_name": ":".join([str(item[value]) for value in value_list[1:]])}
            for item in queryset
        ]
        return ListResult(results=results, count=len(results))

    def list_attr(self, **options):
        """
        通过属性配置权限会用到, 没有属性权限管控不需要实现
        属性列表
        """
        return ListResult(results=[], count=0)

    def list_attr_value(self, filter, page, **options):
        """
        通过属性配置权限会用到, 没有属性权限管控不需要实现
        属性值列表
        注意, 有翻页; 需要返回count
        """
        return ListResult(results=[], count=0)

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

        if filter.get("search") or filter.get("keyword"):
            keyword = filter.get("search") or filter.get("keyword")
            conditions.update({f"{filter.keyword_field}__icontains": keyword})

        return self._list_instance(
            obj_model=filter.model, condition=conditions, value_list=filter.value_list, page=page
        )

    def search_instance(self, filter, page, **options):
        """
        实例搜索的时候会用到
        """
        return self.list_instance(filter, page, **options)

    def list_instance_by_policy(self, filter, page, **options):
        """
        动态查询资源实例进行预览
        """
        return ListResult(results=[], count=0)

    def fetch_instance_info(self, filter, **options):
        """
        批量获取资源实例详情
        """
        value_list = filter.get("attrs") or [self.resource_meta.attribute, "display_name", "_bk_iam_path_"]
        return self._fetch_instance_info(
            obj_model=self.model, resource_meta=self.resource_meta, value_list=value_list, filter=filter
        )
