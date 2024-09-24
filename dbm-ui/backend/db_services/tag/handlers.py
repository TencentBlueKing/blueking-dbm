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

from django.db.models import ManyToManyRel
from django.utils.translation import gettext_lazy as _

from backend.db_meta.models import Tag
from backend.db_services.tag.constants import TAG_RELATED_RESOURCE_DISPLAY_FIELD, TagResourceType
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
        if not resource_type:
            return []

        # 资源类型与展示字段映射
        data: List[Dict] = []
        # 1. 查询dbm内部关联资源
        for field in Tag._meta.get_fields():
            # 非此关联资源，忽略
            if not isinstance(field, ManyToManyRel) or (resource_type and field.name != resource_type):
                continue

            # 查询关联资源并按照标签聚合
            tag__resource_list = defaultdict(list)
            related_objs = field.related_model.objects.prefetch_related("tags").filter(tags__in=ids)
            for obj in related_objs:
                for tag in obj.tags:
                    tag__resource_list[tag.id].append(obj)

            # 填充关联资源信息
            display_field = TAG_RELATED_RESOURCE_DISPLAY_FIELD[resource_type]
            for tag_id in ids:
                related_objs = tag__resource_list[tag_id]
                related_resources = [{"id": obj.pk, "display": getattr(obj, display_field)} for obj in related_objs]
                data.append({"id": tag_id, "related_resources": related_resources})

        # 2. 查询第三方服务关联资源（如资源池、后续可能扩展的别的服务）

        if resource_type == TagResourceType.DB_RESOURCE.value:
            # 资源池根据标签聚合数量
            data = [{"id": tag_id, "ip_count": 0} for tag_id in ids]

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
