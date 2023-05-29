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
from dataclasses import asdict, dataclass
from typing import Dict, List, Union

from django.utils.translation import ugettext as _
from iam import Resource

from backend.db_meta.models import AppCache
from backend.iam_app.exceptions import ResourceNotExistError


@dataclass
class ResourceMeta(metaclass=abc.ABCMeta):
    """
    resource 属性定义
    """

    system_id: str
    id: str
    name: str = ""
    lockup_field: str = ""
    selection_mode: str = "instance"
    related_instance_selections: List = None

    def to_json(self) -> Dict:
        return asdict(self)

    @classmethod
    def _create_simple_instance(cls, instance_id: str, attr=None) -> Resource:
        attr = attr or {}
        return Resource(cls.system_id, cls.id, str(instance_id), attr)

    @classmethod
    def create_instance(cls, instance_id: str, attr=None) -> Resource:
        """
        创建一个Resource，用于make_request中
        :param instance_id: 实例ID
        :param attr: 属性的kv对, 注如果存在拓扑结构则一定加上 _bk_iam_path_ 属性
        """
        raise NotImplementedError


@dataclass
class BusinessResourceMeta(ResourceMeta):
    """
    业务resource 属性定义
    """

    system_id: str = "bk_cmdb"
    id: str = "biz"
    name: str = _("业务")
    lockup_field: str = "bk_biz_id"
    selection_mode: str = "instance"
    related_instance_selections: List = None

    def __post_init__(self):
        self.related_instance_selections = [{"system_id": "bk_cmdb", "id": "business", "ignore_iam_path": True}]

    @classmethod
    def create_instance(cls, instance_id: str, attr=None) -> Resource:
        resource = cls._create_simple_instance(instance_id, attr)
        try:
            bk_biz_name = AppCache.objects.get(bk_biz_id=instance_id).bk_biz_name
        except AppCache.DoesNotExist:
            bk_biz_name = ""
        resource.attribute = {"id": str(instance_id), "name": str(bk_biz_name)}

        return resource


class ResourceEnum:
    """
    resource 枚举类
    """

    BUSINESS = BusinessResourceMeta()

    @classmethod
    def get_resource_by_id(cls, resource_id: Union[ResourceMeta, str]):
        if isinstance(resource_id, ResourceMeta):
            return resource_id

        if resource_id not in cls.__dict__:
            raise ResourceNotExistError(_("资源类型ID不存在: {}").format(resource_id))

        return cls.__dict__[resource_id]


_all_resources = {resource.id: resource for resource in ResourceEnum.__dict__.values() if hasattr(resource, "id")}
