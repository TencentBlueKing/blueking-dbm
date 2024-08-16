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


class TagHandler:
    """标签的操作类"""

    def batch_set_tags(self, tag_ids: List[int]):
        """
        给资源批量设置标签
        """
        # 1. 判断标签中 key 是否允许多值

        # 2. 批量设置标签
        pass

    def delete_tags(self, tag_ids: List[int]):
        """
        删除标签
        """
        # 1. 检查标签是否被引用

        # 2. 批量删除标签

    def create_tags(self, tags: List[Dict[str, str]]):
        """
        批量创建标签
        """

    def list_tags(self):
        """
        标签列表
        """
