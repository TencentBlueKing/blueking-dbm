# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

------------------------------------------------------------------------------

SQLServer 流程输出摘要通用组件。

模块职责：
  - 将 SQLServer 流程节点在执行期产出的结构化摘要行，按调用方指定的"语义预设"
    (`backend/flow/utils/sqlserver/flow_output_presets/`) 写入 FlowSummary，供前端"执行摘要"展示。
  - Component 本身不绑定任何具体表结构；具体表结构由 kwargs["preset"] 指定的
    预设 Serializer 决定。

设计要点 / 数据源 / 调用通道：
  - **继承 MySQL 底座，仅覆盖类属性 `_PRESET_REGISTRY`**：MySQL 父类把注册表声明为
    :class:`MysqlFlowOutputSummaryService` 的类属性，并在 `_execute` 中通过
    `self._PRESET_REGISTRY` 访问；SQLServer 子类在类体内重新声明同名类属性即可完成
    "语义预设命名空间切换"，`_execute` 主流程零复制、零改动。
  - 语义预设 -> Serializer 类 的映射通过 `SqlserverFlowOutputSummaryService._PRESET_REGISTRY`
    类属性承载；新增 SQLServer 独立预设时，先在 `backend/flow/utils/sqlserver/flow_output_presets/`
    目录扩展 Serializer 后，在本类注册表登记一行即可。
  - 幂等能力沿用预设 Serializer 的 `table_primary_key`；本组件不做额外去重。
  - 底层通过 FlowOutputHandler.insert_data 写入，事务已在 handler 内部处理。

边界：
  - 行为与 mysql 侧通用组件 100% 对齐；仅注册表命名空间不同（SQLServer 预设的 `table_name`
    以 `sqlserver_` 前缀）。
  - 无关联 Flow（如临时 pipeline，无 ticket.models.Flow 记录） -> 跳过写入、返回 True，
    与 mysql 侧 / RedisApplySummaryService 保持一致，不阻塞流程。
  - kwargs.preset 未在 SQLServer 注册表登记 -> 记录 error 日志并返回 False（节点显式失败）。
  - kwargs.items 为空列表 -> 视为 no-op，返回 True。
"""

import logging
from typing import Dict, Type

from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.mysql.flow_output_summary import MysqlFlowOutputSummaryService
from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer
from backend.flow.utils.sqlserver.flow_output_presets import SqlserverClusterApplySummarySerializer

logger = logging.getLogger("flow")


class SqlserverFlowOutputSummaryService(MysqlFlowOutputSummaryService):
    """SQLServer 流程输出摘要通用 Service。

    功能说明：
      - 从 kwargs 读取 preset (语义预设短名) 与 items (待写入行列表)，
        依据 `_PRESET_REGISTRY` 定位对应预设 Serializer 类，
        调用 FlowOutputHandler.insert_data 完成写入。
      - 通过"一个 Component + 预设短名"覆盖 SQLServer 全量语义摘要，避免为每个语义单独造 Component。
      - **继承 MySQL 父类 `_execute` 零改动**：仅在类体内覆盖类属性 `_PRESET_REGISTRY`
        指向 SQLServer 独立命名空间的注册表；父类 `_execute` 通过 `self._PRESET_REGISTRY`
        访问时，依 Python 类属性 MRO 规则自动命中子类覆盖版本。

    输入参数（即 kwargs 字段结构）：
      - preset (str, 必填, 非空): 语义预设短名，必须为 `_PRESET_REGISTRY` 已登记的键
      - items (list[dict], 必填): 待写入的摘要行列表，每一行结构必须匹配对应预设 Serializer 字段
      - global_data (dict, 可选): 由 pipeline 框架传入，用于激活国际化

    输出：
      - _execute 返回 bool：True 表示写入成功（含 no-op 场景）；False 表示 preset 非法或异常。
      - 副作用：将 items 追加/合并到 FlowSummary.summary 中对应 `sqlserver_*` 表的 values 数组。

    边界 / 异常：
      - kwargs.preset 未登记 -> 记录 error 日志，返回 False（节点显式失败，便于排障）。
      - kwargs.items 为空列表 -> 记录 info 日志，返回 True（no-op，不阻塞流程）。
      - 流程未关联 Flow (临时 root_id) -> 记录 info 日志，返回 True。
      - 预设 Serializer 字段校验失败 -> FlowOutputHandler.insert_data 内部抛 ValidationError，
        经 BaseService.execute 捕获后 return False。
      - 重复主键写入 -> 依赖 insert_data 的主键合并分支覆盖旧行，天然幂等（详见预设 Serializer docstring）。
    """

    #: SQLServer 语义预设注册表：kwargs["preset"] 字符串 -> 预设 Serializer 类。
    #: 覆盖父类 :attr:`MysqlFlowOutputSummaryService._PRESET_REGISTRY`，切换至 SQLServer 独立
    #: 命名空间（表名以 `sqlserver_` 前缀）。
    #: 新增 SQLServer 预设时，先在 backend/flow/utils/sqlserver/flow_output_presets/ 目录扩展 Serializer，
    #: 再在此登记一行即可；键约定为语义短名（无 sqlserver_ 前缀）。
    _PRESET_REGISTRY: Dict[str, Type[BaseFlowOutputSerializer]] = {
        "cluster_apply": SqlserverClusterApplySummarySerializer,
    }


class SqlserverFlowOutputSummaryComponent(Component):
    """SQLServer 流程输出摘要通用组件。

    使用方式（在 bamboo pipeline 节点中）：
      pipeline.add_act(
          act_name=_("写入集群交付摘要"),
          act_component_code=SqlserverFlowOutputSummaryComponent.code,
          kwargs={
              "preset": "cluster_apply",
              "items": [
                  {"cluster_domain_and_port": "c1.sqlserver.example.db:1433", ...},
                  ...
              ],
          },
      )

    边界 / 备注：
      - Component 本身无状态；具体表结构、字段校验、幂等语义均由 preset 对应的
        flow_output_presets 预设 Serializer 决定。
      - 新增 SQLServer 语义预设需在 :attr:`SqlserverFlowOutputSummaryService._PRESET_REGISTRY`
        类属性中登记一行。
    """

    name = __name__
    code = "sqlserver_flow_output_summary"
    bound_service = SqlserverFlowOutputSummaryService
