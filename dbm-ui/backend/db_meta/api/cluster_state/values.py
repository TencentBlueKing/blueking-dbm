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
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.db_meta.enums import StateDetailType


@dataclass
class StateValue:
    """单个集群单个字段的读取结果"""

    # 字段取值，类型由字段的 value_type 决定；未采集时为 None
    value: Any
    # 展示文本：ENUM 取 choices 的 label，BOOL 为 是/否，其余为 str(value)
    display: str = ""
    # 补充信息，Stored 字段为 extra_class 实例，Native 字段由字段自行决定
    detail: Any = None
    # 最近一次写入时间，只有 Stored 字段有值
    updated_at: Optional[datetime] = None

    def detail_dict(self) -> Optional[Dict[str, Any]]:
        """detail 转为 dict，dataclass 用 asdict 展开"""
        if self.detail is None:
            return None
        if is_dataclass(self.detail):
            return asdict(self.detail)
        return self.detail

    def to_dict(self) -> Dict[str, Any]:
        """接口输出格式"""
        return {
            "value": self.value,
            "display": self.display,
            "detail": self.detail_dict(),
            "updated_at": self.updated_at,
        }


@dataclass
class StateDetail:
    """单元格下钻的内容，由字段的 get_detail 返回，详情接口原样下发"""

    # 展示形式 StateDetailType，决定 data 的结构
    type: str
    # TABLE：行数据列表，每行是 {column_key: value}；KV：{key: value}；TIMELINE 的结构在字段接入时约定
    data: Any
    # 列名 [(key, name)]，与 choices 一样用元组声明；TABLE 为表头，KV 为各 key 的展示名
    columns: List[Tuple[str, str]] = field(default_factory=list)

    @classmethod
    def table(cls, columns: List[Tuple[str, str]], data: List[Dict[str, Any]]) -> "StateDetail":
        """表格：columns 为表头 [(key, name)]，data 为行列表，每行 {key: value}"""
        return cls(type=StateDetailType.TABLE.value, data=data, columns=columns)

    @classmethod
    def kv(cls, columns: List[Tuple[str, str]], data: Dict[str, Any]) -> "StateDetail":
        """键值对：columns 为各 key 的展示名 [(key, name)]，data 为 {key: value}"""
        return cls(type=StateDetailType.KV.value, data=data, columns=columns)

    def to_dict(self) -> Dict[str, Any]:
        """接口输出格式，columns 转为 [{key, name}]"""
        return {
            "type": self.type,
            "columns": [{"key": key, "name": name} for key, name in self.columns],
            "data": self.data,
        }
