# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像 - MySQL 类维度契约。

模块职责：
    - 声明 MySQL 相关的所有巡检维度契约（code + name + description）
    - MySQL 团队专属命名空间；与 Redis / MongoDB / SQLServer 等其它 DB **完全隔离**，
      即使 code 命名相同（如 ``config_check``）也互不干扰

扩展方式：
    1) 在 :class:`MysqlPortraitDimensionCode` 里新增一个 ``EnumField`` 成员
    2) 在下方 ``_DESCRIPTIONS`` 里补一条 description（与成员一一对应）
    3) 巡检 task 里调 ``ingest_summary(db_type=DBType.MySQL, dimension=..., ...)``
       —— 首次运行即自动懒注册到 tb_portrait_dimension_registry

边界：
    - description 与枚举成员均在本模块内定义，静态可读；未在 ``_DESCRIPTIONS`` 中登记的
      成员，其 :attr:`MysqlPortraitDimensionCode.description` 返回空串（运行时兜底，不抛异常）
"""
from typing import Dict

from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrOrPromise

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class MysqlPortraitDimensionCode(StrStructuredEnum):
    """MySQL 集群画像维度契约枚举（本枚举内 code 唯一）。

    每一个成员 = 一个 (code, name, description) 三元契约：
        - ``value``（EnumField 第 1 参数）= code：稳定短码，同枚举内唯一；对应注册表 code 字段
        - ``label``（EnumField 第 2 参数）= 中文名，用于前端展示 / LLM prompt
        - :attr:`description` = 语义描述，从本模块 :data:`_DESCRIPTIONS` 局部字典读取

    典型使用（MySQL 巡检开发者）::
        from datetime import datetime
        from backend.configuration.constants import DBType
        from backend.db_report.portrait import MysqlPortraitDimensionCode, ingest_summary

        ingest_summary(
            db_type=DBType.MySQL,
            dimension=MysqlPortraitDimensionCode.SLOW_QUERY,
            bk_biz_id=100001,
            cluster_domain="a.b.c",
            report_time=datetime.now(),
            summary="近 24h 慢日志同比 +32%，Top1 SQL 未走索引",
            detail_url="https:/xxx/mysql/slowlog/detail?xxx",
        )

    线程安全：是（枚举本身不可变）
    边界：新增成员建议同步补 :data:`_DESCRIPTIONS`；未登记时 description 返回空串
    """

    SLOW_QUERY = EnumField("slow_query", _("MySQL 慢日志巡检"))
    CLUSTER_SKEW = EnumField("cluster_skew", _("MySQL 集群倾斜巡检"))
    CONFIG_CHECK = EnumField("config_check", _("MySQL 配置项巡检"))
    TENDBHA_META_CHECK = EnumField("TENDBHA_META_CHECK", _("TenDBHA 集群拓扑检查"))
    TENDBCLUSTER_META_CHECK = EnumField("TENDCLUSTER_META_CHECK", _("TenDBCluster 集群拓扑检查"))
    MYSQL_CHECKSUM_CHECK = EnumField("MYSQL_CHECKSUM_CHECK", _("TenDBHA/TenDBCluster 数据校验"))
    MYSQL_BACKUP_CHECK = EnumField("MYSQL_BACKUP_CHECK", _("MySQL 备份巡检"))
    MYSQL_BINLOG_CHECK = EnumField("MYSQL_BINLOG_CHECK", _("MySQL BINLOG巡检"))
    MYSQL_EXPORTER_CHECK = EnumField("MYSQL_EXPORTER_CHECK", _("MySQL Exporter巡检"))

    @property
    def description(self) -> str:
        """获取当前枚举成员的语义描述。

        :return: description 文本；未登记时返回空串（不抛异常，运行时兜底）
        边界：description 集中维护在同模块 :data:`_DESCRIPTIONS`，保持"代码即事实源"
        """
        return str(_DESCRIPTIONS.get(self, ""))


#: MySQL 维度描述表：``<枚举成员> -> description 文本``（模块私有，外部通过成员的 .description 属性访问）
#: 与枚举成员分离维护的原因：
#:   1) 保持枚举成员定义单行紧凑
#:   2) description 通常较长；写在 EnumField 里会破坏 StrStructuredEnum (value/label) 二元约定
#:   3) 便于集中翻译

_DESCRIPTIONS: Dict[MysqlPortraitDimensionCode, StrOrPromise] = {
    MysqlPortraitDimensionCode.SLOW_QUERY: _("慢查询总量、TOP SQL 特征、无索引扫描等；点击详情可查看完整 AI 分析结果"),
    MysqlPortraitDimensionCode.CLUSTER_SKEW: _("集群分片间的数据与流量倾斜巡检；点击详情可查看完整 AI 分析结果"),
    MysqlPortraitDimensionCode.CONFIG_CHECK: _("MySQL 配置合理性与一致性 AI 巡检；点击详情可查看完整分析报告"),
    MysqlPortraitDimensionCode.TENDBHA_META_CHECK: _("TenDBHA 集群拓扑完整性检查"),
    MysqlPortraitDimensionCode.TENDBCLUSTER_META_CHECK: _("TenCluster 集群拓扑完整性检查"),
    MysqlPortraitDimensionCode.MYSQL_CHECKSUM_CHECK: _("数据一致性校验"),
}
