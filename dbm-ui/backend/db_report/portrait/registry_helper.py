# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像 - 维度注册表访问封装。

模块职责：
    - 统一封装对 ``PortraitDimensionRegistry`` 的**写侧**访问，供 SDK 上报路径共用
    - 屏蔽 ORM 细节，暴露语义化方法

设计要点（enabled 语义澄清）：
    - ``enabled`` **只影响"读侧"**：Agent 生成画像报告时，禁用的维度不会被纳入分析
    - ``enabled`` **不影响"写侧"**：SDK 上报摘要时不校验 enabled；只要维度已注册即可写入
    - 这样做的原因：禁用是运维旁路开关，不该反向侵入到业务方（各巡检 task）的执行逻辑

设计要点（宽松自动注册策略）：
    - SDK 写入前调 :meth:`ensure_registered`：**未注册则自动创建；已注册则原样返回，不回写元数据**
    - 契约由 :class:`PortraitDimensionCode` 枚举提供，SDK 入参层就已经过编译期约束，
      不会出现拼写错误污染注册表——因此可以放心自动注册
    - name / description 只在"首次注册"时以枚举当前值落库；后续任何一方（运维后台 / 人工修订 /
      未来的运营别名功能）修改都不会被 SDK 覆盖，避免多写入路径互相打架

设计要点（并发安全）：
    - 首次注册使用 ``get_or_create``；ORM 层原子实现 + 唯一键 (db_type, code) 兜底，
      同一 (db_type, code) 并发首建时只会有一条 create 成功，其余走 get 分支

暴露方法：
    - :meth:`ensure_registered`：写侧懒注册；不存在则 create，已存在则原样返回

设计边界：
    - 读侧（Agent / MCP 工具）目前直接查询 :class:`PortraitDimensionRegistry` ORM，不经本类；
      如未来出现多处读侧复用需求，再补充读侧方法
"""
from backend.db_report.enums.portrait import DEFAULT_DIMENSION_WEIGHT
from backend.db_report.models.portrait_dimension_registry import PortraitDimensionRegistry


class RegistryHelper:
    """维度注册表访问封装（当前仅承载写侧懒注册）。

    职责：
        - 提供"写侧懒注册"通道，供 SDK ``ingest_summary`` 上报前调用
        - 显式区分 enabled 语义：只对读侧生效，不影响写入

    使用方式::

        # 写侧（SDK 上报前）：未注册自动创建；已注册原样返回，不回写 name/description
        RegistryHelper.ensure_registered(
            db_type="mysql", code="slow_query",
            name="MySQL 慢日志巡检", description="...",
        )

    边界：
        - 本类为纯服务；不管理 enabled 启停（启停走 sync_portrait_dimensions command）
        - 读侧访问目前由调用方直接查询 :class:`PortraitDimensionRegistry` ORM 完成
    """

    @classmethod
    def ensure_registered(
        cls,
        db_type: str,
        code: str,
        name: str,
        description: str = "",
    ) -> PortraitDimensionRegistry:
        """写侧懒注册：不存在则原子创建，已存在则原样返回。

        语义：
            - 契约由上游 :class:`PortraitDimensionCode` 枚举保证 (db_type, code) 的正确性
            - name / description **仅在首次注册时**落库；后续不再由 SDK 回写
              （避免与运维后台 / 人工修订等其他写入路径互相覆盖）
            - weight **仅在首次注册时**落库，取默认常量 :data:`DEFAULT_DIMENSION_WEIGHT`
              （0.5，中等重要）；之后运维可在注册表上自由调整，SDK 不回写
            - **不修改 enabled / summary_fetch_strategy**：二者均为管理侧字段，SDK 上报路径
              既不设置也不回写；enabled 由 ``sync_portrait_dimensions`` command 显式启停，
              summary_fetch_strategy 走模型默认值（all）

        :param db_type: 数据库类型（DBType.value）
        :param code: 维度短码
        :param name: 维度中文名（仅首次注册时落库；来自 :class:`PortraitDimensionCode` 的 label）
        :param description: 维度描述文本（仅首次注册时落库；可空）
        :return: :class:`PortraitDimensionRegistry` 实例

        边界：
            - 首次调用     -> 新建，enabled 默认 True，name/description 按入参落库，
                              weight 取默认常量 DEFAULT_DIMENSION_WEIGHT（0.5）；
                              summary_fetch_strategy 不设置，走模型默认值（all）
            - 已存在        -> 原样返回，不回写任何字段（含 name/description/enabled/weight/summary_fetch_strategy）
            - 并发首次调用  -> 由 ``get_or_create`` + 唯一键 (db_type, code) 兜底，
                              只会有一条 create 成功，其余无冲突地走 get 分支
        """

        obj, _created = PortraitDimensionRegistry.objects.get_or_create(
            db_type=db_type,
            code=code,
            defaults={
                # defaults 仅在"新建"路径生效；已存在时完全不参与写入
                "name": name,
                "description": description or "",
                "enabled": True,
                # 首次注册给"中等重要"默认权重；后续运维可自由调整，SDK 不覆盖
                "weight": DEFAULT_DIMENSION_WEIGHT,
            },
        )
        return obj
