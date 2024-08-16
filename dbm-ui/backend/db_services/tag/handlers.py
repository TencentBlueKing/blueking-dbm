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

from django.db.models import ManyToManyRel
from django.utils.translation import gettext_lazy as _

from backend.db_meta.models import Tag
from backend.db_services.tag.constants import TagResourceType
from backend.exceptions import ValidationError


class TagHandler:
    """标签的操作类"""

    def batch_set_tags(self, tag_ids: List[int]):
        """
        给资源批量设置标签
        """
        # 1. 判断标签中 key 是否允许多值

        # 2. 批量设置标签
        pass

    @classmethod
    def delete_tags(cls, bk_biz_id: int, ids: List[int]):
        """
        删除标签
        """
        # 1. 检查标签是否被引用
        related_resources = cls.query_related_resources(ids)
        for related_resource in related_resources:
            if related_resource["count"] > 0:
                raise ValidationError(_("标签被引用，无法删除"))

        # 2. 批量删除标签
        Tag.objects.filter(bk_biz_id=bk_biz_id, id__in=ids).delete()

    @classmethod
    def query_related_resources(cls, ids: List[int], resource_type: str = None):
        """
        查询关联资源
        """
        # 1. 查询外键关联资源
        data = []
        for tag_id in ids:
            info = {"id": tag_id, "related_resources": []}
            for field in Tag._meta.get_fields():
                if isinstance(field, ManyToManyRel) and (field.name == resource_type or resource_type is None):
                    related_objs = field.related_model.objects.prefetch_related("tags").filter(tags__id=tag_id)
                    info["related_resources"].append(
                        {
                            "resource_type": field.name,
                            "count": related_objs.count(),
                        }
                    )

            # 2. 查询第三方服务关联资源（如资源池、后续可能扩展的别的服务）
            if resource_type == TagResourceType.DB_RESOURCE.value or resource_type is None:
                info["related_resources"].append(
                    {
                        "resource_type": TagResourceType.DB_RESOURCE.value,
                        # TODO 请求资源池接口得到统计数量
                        "count": 0,
                    }
                )
            data.append(info)
        return data

    @classmethod
    def batch_create(cls, bk_biz_id: int, tags: List[Dict[str, str]], creator: str = ""):
        """
        批量创建标签
        """
        duplicate_tags = cls.verify_duplicated(bk_biz_id, tags)
        if duplicate_tags:
            raise ValidationError(_("检查到重复的标签"), data=duplicate_tags)

        tag_models = [Tag(bk_biz_id=bk_biz_id, key=tag["key"], value=tag["value"], creator=creator) for tag in tags]
        Tag.objects.bulk_create(tag_models)

    @classmethod
    def verify_duplicated(cls, bk_biz_id: int, tags: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        检查标签是否重复
        """
        biz_tags = [f"{tag.key}:{tag.value}" for tag in Tag.objects.filter(bk_biz_id=bk_biz_id)]
        duplicate_tags = []
        for tag in tags:
            if f'{tag["key"]}:{tag["value"]}' in biz_tags:
                duplicate_tags.append(tag)
        return duplicate_tags
