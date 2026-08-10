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

mysql/spider 流程输出摘要通用组件。

模块职责：
  - 将 mysql/spider 流程节点在执行期产出的结构化摘要行，按调用方指定的"语义预设"
    (flow_output_presets)写入 FlowSummary，供前端"执行摘要"展示。
  - Component 本身不绑定任何具体表结构；具体表结构由 kwargs["preset"] 指定的
    预设 Serializer 决定。

设计要点 / 数据源 / 调用通道：
  - 一个 Component 覆盖 mysql/spider 所有语义摘要输出，避免"每语义一 Component"膨胀。
  - 语义预设 -> Serializer 类 的映射通过模块级注册表 _PRESET_REGISTRY 承载；
    新增预设时，在 flow_output_presets 目录扩展 Serializer 后，在该注册表登记一行即可。
  - 幂等能力沿用预设 Serializer 的 `table_primary_key`；本组件不做额外去重。
  - 底层通过 FlowOutputHandler.insert_data 写入，事务已在 handler 内部处理。

边界：
  - 无关联 Flow(如 DTS 临时 pipeline，无 ticket.models.Flow 记录) -> 跳过写入、返回 True，
    与既有 RedisApplySummaryService 保持一致，不阻塞流程。
  - kwargs.preset 未登记 / kwargs.items 缺失 -> 记录 error 日志并返回 False，让节点显式失败。
  - kwargs.items 为空列表 -> 视为 no-op，返回 True。
"""

import logging
from typing import Dict, List, Type

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.flow_output import BaseFlowOutputSerializer, FlowOutputHandler
from backend.flow.utils.mysql.flow_output_presets import (
    AuthResultSummarySerializer,
    ClusterApplySummarySerializer,
    InstanceChangeSummarySerializer,
    MessageSummarySerializer,
    PrecheckResultSummarySerializer,
    SqlExecResultSummarySerializer,
)
from backend.ticket.models import Flow

logger = logging.getLogger("flow")

#: 语义预设注册表：kwargs["preset"] 字符串 -> 预设 Serializer 类。
#: 新增语义预设时，先在 backend/flow/utils/mysql/flow_output_presets/ 目录扩展 Serializer，
#: 再在此登记一行即可；键约定为语义短名（无 mysql_ 前缀）。
_PRESET_REGISTRY: Dict[str, Type[BaseFlowOutputSerializer]] = {
    "cluster_apply": ClusterApplySummarySerializer,
    "instance_change": InstanceChangeSummarySerializer,
    "auth_result": AuthResultSummarySerializer,
    "precheck": PrecheckResultSummarySerializer,
    "sql_exec": SqlExecResultSummarySerializer,
    "message": MessageSummarySerializer,
}


class MysqlFlowOutputSummaryService(BaseService):
    """mysql/spider 流程输出摘要通用 Service。

    功能说明：
      - 从 kwargs 读取 preset (语义预设短名) 与 items (待写入行列表)，
        依据 _PRESET_REGISTRY 定位对应预设 Serializer 类，调用 FlowOutputHandler.insert_data 完成写入。
      - 通过"一个 Component + 预设短名"覆盖 mysql/spider 全量语义摘要，避免为每个语义单独造 Component。

    输入参数（即 kwargs 字段结构）：
      - preset (str, 必填, 非空): 语义预设短名，必须为 _PRESET_REGISTRY 已登记的键
      - items (list[dict], 必填): 待写入的摘要行列表，每一行结构必须匹配对应预设 Serializer 字段
      - global_data (dict, 可选): 由 pipeline 框架传入，用于激活国际化

    输出：
      - _execute 返回 bool：True 表示写入成功（含 no-op 场景）；False 表示 preset 非法或异常。
      - 副作用：将 items 追加/合并到 FlowSummary.summary 中对应 table_name 的 values 数组。

    边界 / 异常：
      - kwargs.preset 未登记 -> 记录 error 日志，返回 False（节点显式失败，便于排障）。
      - kwargs.items 为空列表 -> 记录 info 日志，返回 True（no-op，不阻塞流程）。
      - 流程未关联 Flow (临时 root_id) -> 记录 info 日志，返回 True（与 RedisApplySummaryService 一致）。
      - 预设 Serializer 字段校验失败 -> FlowOutputHandler.insert_data 内部抛 ValidationError，
        经 BaseService.execute 捕获后 return False。
      - 重复主键写入 -> 依赖 insert_data 的主键合并分支覆盖旧行，天然幂等（详见预设 Serializer docstring）。
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs: Dict = data.get_one_of_inputs("kwargs") or {}
        preset_key: str = kwargs.get("preset", "") or ""
        items: List[Dict] = kwargs.get("items") or []
        root_id: str = self.runtime_attrs.get("root_pipeline_id")

        # 1) 校验 preset 合法性
        slz_cls = _PRESET_REGISTRY.get(preset_key)
        if slz_cls is None:
            self.log_error(_("摘要预设 preset=[{}] 未登记，可选值：{}").format(preset_key, sorted(_PRESET_REGISTRY)))
            return False

        # 2) items 为空视为 no-op，不阻塞流程
        if not items:
            self.log_info(_("preset=[{}] items 为空，跳过摘要写入").format(preset_key))
            return True

        # 3) 兜底：无关联 Flow 的临时流程（如 DTS 内部临时 pipeline）直接跳过，行为对齐 RedisApplySummaryService
        if not Flow.objects.filter(flow_obj_id=root_id).exists():
            self.log_info(_("当前流程[{}]未关联单据Flow记录，跳过写入执行摘要").format(root_id))
            return True

        # 4) 一次性写入；相同 table_primary_key 的重复写入会走 insert_data 的合并覆盖分支，天然幂等
        FlowOutputHandler(slz_cls).insert_data(root_id, items)
        self.log_info(_("preset=[{}] 已写入 {} 行摘要到 table_name=[{}]").format(preset_key, len(items), slz_cls.table_name))
        return True


class MysqlFlowOutputSummaryComponent(Component):
    """mysql/spider 流程输出摘要通用组件。

    使用方式（在 bamboo pipeline 节点中）：
      pipeline.add_act(
          act_name=_("写入集群交付摘要"),
          act_component_code=MysqlFlowOutputSummaryComponent.code,
          kwargs={
              "preset": "cluster_apply",
              "items": [
                  {"cluster_domain_and_port": "c1.mysql.example.db:3306", ...},
                  ...
              ],
          },
      )

    边界 / 备注：
      - Component 本身无状态；具体表结构、字段校验、幂等语义均由 preset 对应的
        flow_output_presets 预设 Serializer 决定。
      - 新增语义预设需在本文件模块级 _PRESET_REGISTRY 登记一行。
    """

    name = __name__
    code = "mysql_flow_output_summary"
    bound_service = MysqlFlowOutputSummaryService
