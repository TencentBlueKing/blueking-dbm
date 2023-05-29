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
from typing import List

from backend.db_meta.models.group import GroupInstance


class GroupHandler:
    """分组的操作类"""

    @classmethod
    def move_instances(cls, new_group: int, instances: List[int]):
        """
        批量将实例移动到一个新的组
        :param new_group: 新组的ID
        :param instances: 被移动的实例ID列表
        """
        resp = GroupInstance.objects.filter(instance_id__in=instances).update(group_id=new_group)

        return resp
