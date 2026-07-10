# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像 - Redis 类维度契约。

模块职责：
    - 声明 Redis 相关的所有巡检维度契约（code + name + description）
    - Redis 团队专属命名空间；与 MySQL / MongoDB / SQLServer 等其它 DB **完全隔离**，
      即使 code 命名相同（如 ``config_check``）也互不干扰

扩展方式：
    1) 在 :class:`RedisPortraitDimensionCode` 里新增一个 ``EnumField`` 成员
    2) 在下方 ``_DESCRIPTIONS`` 里补一条 description（与成员一一对应）
    3) 巡检 task 里调 ``ingest_summary(db_type=DBType.Redis, dimension=..., ...)``
       —— 首次运行即自动懒注册到 tb_portrait_dimension_registry

边界：
    - description 与枚举成员均在本模块内定义，静态可读；未在 ``_DESCRIPTIONS`` 中登记的
      成员，其 :attr:`RedisPortraitDimensionCode.description` 返回空串（运行时兜底，不抛异常）
"""
from typing import Dict

from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrOrPromise

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class RedisPortraitDimensionCode(StrStructuredEnum):
    """Redis 集群画像维度契约枚举（本枚举内 code 唯一）。

    每一个成员 = 一个 (code, name, description) 三元契约：
        - ``value``（EnumField 第 1 参数）= code：稳定短码，同枚举内唯一；对应注册表 code 字段
        - ``label``（EnumField 第 2 参数）= 中文名，用于前端展示 / LLM prompt
        - :attr:`description` = 语义描述，从本模块 :data:`_DESCRIPTIONS` 局部字典读取

    典型使用（Redis 巡检开发者）::
        from datetime import datetime
        from backend.configuration.constants import DBType
        from backend.db_report.portrait import RedisPortraitDimensionCode, ingest_summary

        ingest_summary(
            db_type=DBType.Redis,
            dimension=RedisPortraitDimensionCode.BIG_KEY,
            bk_biz_id=100001,
            cluster_domain="a.b.c",
            report_time=datetime.now(),
            summary="发现 3 个 >10MB 大 Key，TOP1: user_profile:xxx",
            detail_url="https:/xxx/redis/big-key/detail?xxx",
        )

    线程安全：是（枚举本身不可变）
    边界：新增成员建议同步补 :data:`_DESCRIPTIONS`；未登记时 description 返回空串
    """

    # 示例占位成员：单下划线前缀表明"仅作模板，非正式业务维度"，
    # Redis 首个真实巡检维度落地后应删除本行，避免被误引用。
    _EXAMPLE = EnumField("_example", _("Redis 示例维度（模板占位，勿在业务代码中引用）"))
    # 后续正式维度新增示例（保留注释形式作为模板）：
    # BIG_KEY = EnumField("big_key", _("Redis 大 Key 巡检"))
    # HOT_KEY = EnumField("hot_key", _("Redis 热 Key 巡检"))
    # CONFIG_CHECK = EnumField("config_check", _("Redis 配置项巡检"))

    @property
    def description(self) -> str:
        """获取当前枚举成员的语义描述。

        :return: description 文本；未登记时返回空串（不抛异常，运行时兜底）
        边界：description 集中维护在同模块 :data:`_DESCRIPTIONS`，保持"代码即事实源"
        """
        return str(_DESCRIPTIONS.get(self, ""))


#: Redis 维度描述表：``<枚举成员> -> description 文本``（模块私有，外部通过成员的 .description 属性访问）
#: 与枚举成员分离维护的原因：
#:   1) 保持枚举成员定义单行紧凑
#:   2) description 通常较长；写在 EnumField 里会破坏 StrStructuredEnum (value/label) 二元约定
#:   3) 便于集中翻译

_DESCRIPTIONS: Dict[RedisPortraitDimensionCode, StrOrPromise] = {
    # 与枚举成员一一对应，按需登记；示例：
    RedisPortraitDimensionCode._EXAMPLE: _("Redis 示例维度（模板占位，勿在业务代码中引用）"),
    # RedisPortraitDimensionCode.BIG_KEY: _("..."),
    # RedisPortraitDimensionCode.HOT_KEY: _("..."),
}
