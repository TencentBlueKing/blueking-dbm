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

import attr


@attr.s(auto_attribs=True)
class DBBaseConfig:
    # 元集群类型/dbconf 命名空间
    meta_cluster_type: str
    # 配置类型
    conf_type: str

    @classmethod
    def from_dict(cls, init_data: Dict) -> "DBBaseConfig":
        return cls(init_data["meta_cluster_type"], init_data["conf_type"])


@attr.s(auto_attribs=True)
class DBConfigLevelData:
    bk_biz_id: str
    # 层级类型
    level_name: str
    # 层级值
    level_value: str
    # level_info 是上层配置信息，目前只有在请求 cluster 配置是需要传他的模块信息
    # 因为 dbconfig 没有跟 dbmeta 通信，他要继承上层配置，不知道 module 信息，需要传递进来
    level_info: Dict[str, str]
    # 版本号 --> conf_file
    version: str

    def __attrs_post_init__(self):
        self.bk_biz_id = str(self.bk_biz_id)
        self.level_value = str(self.level_value)

    @classmethod
    def from_dict(cls, init_data: Dict) -> "DBConfigLevelData":
        return cls(
            init_data["bk_biz_id"],
            init_data["level_name"],
            init_data["level_value"],
            init_data.get("level_info", {}),
            init_data["version"],
        )


@attr.s(auto_attribs=True)
class UpsertConfigData:
    # 配置参数列表
    conf_items: List[Dict[str, str]]
    description: str
    publish_description: str
    confirm: int

    @classmethod
    def from_dict(cls, init_data: Dict) -> "UpsertConfigData":
        return cls(
            init_data["conf_items"],
            init_data.get("description", ""),
            init_data.get("publish_description", ""),
            init_data["confirm"],
        )


@attr.s(auto_attribs=True)
class DBConfigDeployData:
    bk_biz_id: str
    module_id: str

    def __attrs_post_init__(self):
        self.bk_biz_id = str(self.bk_biz_id)
        self.module_id = str(self.module_id)

    @classmethod
    def from_dict(cls, init_data: Dict) -> "DBConfigDeployData":
        return cls(
            init_data["bk_biz_id"],
            init_data["module_id"],
        )
