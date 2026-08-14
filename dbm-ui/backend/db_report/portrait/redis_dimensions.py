# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
the specific language governing permissions and limitations under the License.

集群画像 - Redis 类维度契约。

模块职责：
    - 声明 Redis 相关的所有巡检维度契约（code + name + description）
    - Redis 团队专属命名空间；与 MySQL / MongoDB / SQLServer 等其它 DB **完全隔离**，
      即使 code 命名相同（如 ``config_check``）也互不干扰

扩展方式：
    1) 在 :class:`RedisPortraitDimensionCode` 里新增一个 ``EnumField`` 成员
    2) 在下方 ``_DESCRIPTIONS`` 里补一条 description（与成员一一对应）
    3) 巡检 task 里调 ``ingest_redis_cluster_summary`` 或 ``ingest_summary(db_type=DBType.Redis, ...)``
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
            dimension=RedisPortraitDimensionCode.RELIABILITY,
            bk_biz_id=100001,
            cluster_domain="a.b.c",
            report_time=datetime.now(),
            summary="[全备] 缺备：3 个分片昨日无全备记录",
            detail_url="",
        )

    线程安全：是（枚举本身不可变）
    边界：新增成员建议同步补 :data:`_DESCRIPTIONS`；未登记时 description 返回空串
    """

    TOPOLOGY_SCALE = EnumField("topology_scale", _("拓扑与规模"))
    LOAD_CAPACITY = EnumField("load_capacity", _("负载与容量"))
    RELIABILITY = EnumField("reliability", _("可靠性与数据安全"))
    CONFIG_HEALTH = EnumField("config_health", _("配置与组件健康"))

    @property
    def description(self) -> str:
        """获取当前枚举成员的语义描述。

        :return: description 文本；未登记时返回空串（不抛异常，运行时兜底）
        边界：description 集中维护在同模块 :data:`_DESCRIPTIONS`，保持"代码即事实源"
        """
        return str(_DESCRIPTIONS.get(self, ""))


#: Redis 维度描述表：``<枚举成员> -> description 文本``（模块私有，外部通过成员的 .description 属性访问）
_DESCRIPTIONS: Dict[RedisPortraitDimensionCode, StrOrPromise] = {
    RedisPortraitDimensionCode.TOPOLOGY_SCALE: _(
        "集群拓扑结构与规模画像。当前态规模（分片 / proxy / 实例数量、规格、版本、region、亲和性）"
        "由 skill 生成时通过 Redis 元数据 MCP 拉取，落入报告头，不经本维度摘要表。"
        "本维度摘要只收拓扑完整性巡检：孤立实例、实例状态非 RUNNING、访问入口绑定与元数据不一致、"
        "主从或 proxy 可用区亲和性违反、同集群规格不一致。"
        "summary 以 [孤立实例] / [实例状态] / [亲和性] / [入口] 等前缀区分子检查来源；"
        "时间窗内无摘要代表拓扑完整、无异常。"
    ),
    RedisPortraitDimensionCode.LOAD_CAPACITY: _(
        "集群负载与容量水位。覆盖 CPU / 内存 / 连接数 / QPS / 磁盘 IO 等负载指标的水位与变化趋势，"
        "内存容量使用率与增长趋势（重点关注 noeviction 策略集群的内存增长风险），"
        "以及分片间的负载倾斜与数据倾斜。"
        "一期暂不写入本维度摘要（容量增长 / 负载倾斜 / 数据倾斜巡检源尚未挂载）；"
        "时间窗内无摘要代表尚无负载与容量巡检数据，不代表已确认健康。"
        "本维度不由画像 agent 实时拉 metrics。"
    ),
    RedisPortraitDimensionCode.RELIABILITY: _(
        "集群可靠性与数据安全。覆盖全量备份是否按 schedule 覆盖（缺备 / 偏班 / 失败）、"
        "TendisPlus 与 SSD 集群从库 binlog 连续性、定期回档演练的成败结果与失败阶段。"
        "summary 以 [全备] / [binlog] / [回档演练] 等前缀区分来源；"
        "备份类异常才上报，演练类每次结束必报（含成功样本）。"
        "时间窗内无摘要代表备份正常且无演练记录。"
    ),
    RedisPortraitDimensionCode.CONFIG_HEALTH: _(
        "集群配置与管控组件健康。覆盖存储节点角色与 INFO REPLICATION 实际状态一致性、"
        "Predixy INFO Servers 异常与磁盘配置文件漂移等配置巡检，"
        "以及 redis / proxy exporter 的 down / duplicate / redundant / 跨集群指标串扰等监控组件异常。"
        "summary 以 [配置] / [exporter] 等前缀区分来源；"
        "异常才上报，时间窗内无摘要代表配置一致、组件健康。"
    ),
}
