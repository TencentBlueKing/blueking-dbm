"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from dataclasses import dataclass


@dataclass()
class Instance:
    """
    定义实例通用结构体
    @attributes host 机器ip，ipv4格式
    @attributes bk_cloud_id 机器所在云区域, 默认值为0
    @attributes port 实例port
    """

    __dataclass_fields__ = None

    host: str
    port: int
    bk_cloud_id: int = 0

    def __init__(self, **kwargs):
        for field in Instance.__dataclass_fields__:
            setattr(self, field, kwargs.get(field))
