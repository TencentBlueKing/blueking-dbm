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
    meta_cluster_type: str
    conf_type: str

    @classmethod
    def from_dict(cls, init_data: Dict) -> "DBBaseConfig":
        return cls(init_data["meta_cluster_type"], init_data["conf_type"])


@attr.s(auto_attribs=True)
class DBConfigLevelData:
    bk_biz_id: str
    level_name: str
    level_value: str
    level_info: Dict[str, str]
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
