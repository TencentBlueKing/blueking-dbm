# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

NameCleaner：flow 节点名称的无损正则清洗器。

模块职责：
  - 对原始 component_name 应用一组预编译正则，将 IP / 端口 / hex / 时间戳等易变 token 替换为占位符
  - 只做"参数化"，不做"合并判断"（合并判断由 NameNormalizer 借助 alias 表 + LLM 完成）
  - 纯确定性、无副作用、线程安全

上下游边界：
  - 上游：FlowSampleCollector 传入原始 raw_name（来自 flow_tree.tree activity.name）
  - 下游：NameNormalizer.normalize() 用清洗结果作为 alias 表查询 key
"""
import logging
from typing import List, Pattern, Tuple

from backend.db_services.flow_node_baseline.constants import MAX_NAME_LENGTH_FOR_NORMALIZE, NAME_CLEAN_RULES

logger = logging.getLogger("root")


class NameCleaner:
    """流程节点名称清洗器：无损正则参数化。

    职责：
      - 应用 constants.NAME_CLEAN_RULES 中定义的一组正则
      - 将 IP / 端口 / hex / 时间戳替换为 <IP> / <PORT> / <HASH> / <TS> 占位符
      - 处理 None / 超长输入的边界情况

    使用方式：
        cleaner = NameCleaner()
        cleaned = cleaner.clean("Redis-1.1.1.1-下发介质包")
        # cleaned == "Redis-<IP>-下发介质包"

    线程安全：是（内部只读取预编译正则，无可变状态）
    副作用：无（纯函数式）
    边界：
      - raw_name 为 None / 空串 → 返回空串
      - raw_name 长度超过 MAX_NAME_LENGTH_FOR_NORMALIZE → 先截断再清洗
      - 未匹配任何规则 → 原样返回（截断后）
    """

    #: 清洗规则表引用（模块加载时预编译，避免运行期重复编译）
    _RULES: List[Tuple[Pattern, str]] = NAME_CLEAN_RULES

    #: 名称截断上限（字符数）
    _MAX_LENGTH: int = MAX_NAME_LENGTH_FOR_NORMALIZE

    def clean(self, raw_name: str) -> str:
        """对单条原始 name 应用全部清洗规则。

        :param raw_name: 原始节点名称，可能包含 IP / 端口 / hex / 时间戳
        :return: 清洗后的字符串；异常输入返回空串
        边界：
          - None / 非 str → 返回空串
          - 超长 → 截断到 _MAX_LENGTH 字符再清洗
          - 未命中任何规则 → 原样返回
        """
        if raw_name is None or not isinstance(raw_name, str):
            return ""

        # 空串直接返回；避免后续正则应用产生额外开销
        if not raw_name:
            return ""

        # 超长先截断，控制后续正则匹配 + LLM prompt 的最大规模
        text: str = raw_name[: self._MAX_LENGTH]

        for pattern, placeholder in self._RULES:
            text = pattern.sub(placeholder, text)

        return text

    def clean_many(self, raw_names: List[str]) -> List[str]:
        """批量清洗；顺序保持与输入一致。

        :param raw_names: 原始名称列表
        :return: 清洗后名称列表；元素与输入一一对应
        边界：输入为空 list → 返回空 list
        """
        if not raw_names:
            return []
        return [self.clean(name) for name in raw_names]
