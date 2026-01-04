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
from .check_affinity import check_redis_affinity
from .check_entry import check_redis_entry_consistency
from .check_instance import check_redis_instance
from .check_role import check_redis_instance_role


def check_redis_clusters():
    """Redis cluster meta data validation"""
    check_redis_instance()
    check_redis_affinity()
    check_redis_instance_role()
    check_redis_entry_consistency()


__all__ = ["check_redis_clusters"]
