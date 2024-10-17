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

from backend.db_meta.models import Tag
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

        # 2. 批量删除标签
        Tag.objects.filter(bk_biz_id=bk_biz_id, id__in=ids).delete()

    @classmethod
    def query_related_resources(cls, bk_biz_id: int, ids: List[int]):
        """
        查询关联资源
        """
        # 1. 查询外键关联资源
        related_fields = []
        for field in Tag._meta.get_fields():
            if isinstance(field, ManyToManyRel):
                related_fields.append(field.name)

        # 2. 查询第三方服务关联资源（如资源池、后续可能扩展的别的服务）

    @classmethod
    def batch_create(cls, bk_biz_id: int, tags: List[Dict[str, str]]):
        """
        批量创建标签
        """
        tag_models = [Tag(bk_biz_id=bk_biz_id, key=tag["key"], value=tag["value"]) for tag in tags]
        Tag.objects.bulk_create(tag_models)

    @classmethod
    def verify_duplicated(cls, bk_biz_id: int, tags: List[Dict[str, str]]):
        """
        检查标签是否重复
        """
        biz_tags = [f"{tag.key}:{tag.value}" for tag in Tag.objects.filter(bk_biz_id=bk_biz_id)]
        duplicate_tags = []
        for tag in tags:
            if f'{tag["key"]}: {tag["value"]}' in biz_tags:
                duplicate_tags.append(tag)
        if duplicate_tags:
            raise ValidationError(f"duplicate tags: {duplicate_tags}")
