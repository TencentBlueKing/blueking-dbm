# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

list_table_status 工具的入参/出参 serializer。

定位：表清单/前置定位工具，与 list_databases 同层，独立于索引分析功能域。
"""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

# order_by 白名单（与 impl.list_table_status.ALLOWED_ORDER_BY 保持同步）
# 仅暴露 5 个核心键，覆盖最常见的"找大表 / 行数多 / 索引膨胀 / 统计过期 / 写入活跃"五类入口
# 注意：ChoiceField 的 choices 用元组而非列表，避免运行时被意外修改
_ALLOWED_ORDER_BY_CHOICES = (
    "total_size_mb",
    "row_count",
    "index_size_mb",
    "stats_outdated_count",
    "last_user_update",
)
_ALLOWED_ORDER_CHOICES = ("desc", "asc")


class SQLServerListTableStatusInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    dbname = serializers.CharField(
        help_text=_("目标业务库名，仅允许 [A-Za-z_][A-Za-z0-9_$#@]{0,127}"),
    )
    schema = serializers.CharField(
        help_text=_("可选 schema 过滤；不传则返回所有 schema 下的用户表"),
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )
    table_name = serializers.CharField(
        help_text=_(
            "可选表名精确过滤，仅允许 [A-Za-z_][A-Za-z0-9_$#@]{0,127}；" "传入后等价于『查这一张表的状态』，limit 自动收敛为 1，" "表不存在时返回空列表，不抛异常"
        ),
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )
    address = serializers.CharField(
        help_text=_("实例地址 ip:port，可选；不传时缺省走 master"),
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )
    limit = serializers.IntegerField(
        help_text=_("返回前 N 条（按总大小倒序）；缺省 200，最大 1000"),
        required=False,
        allow_null=True,
        default=None,
    )
    verbose = serializers.ChoiceField(
        help_text=_(
            "输出粒度（三态枚举，互斥）。"
            "summary（默认）：仅 schema_name/table_name/row_count/total_size_mb 4 个字段，"
            "token 友好，适合浏览全库表清单；"
            "detail：返回 20 个全字段，索引分析等深度场景使用；"
            "count_only：跳过明细查询，仅返回 total_user_table_count（叠加 schema/table_name 过滤后），"
            "tables 为空数组、limit 置 0；用于回答『这个库一共有多少张用户表』；"
            "此模式下 order_by / order 静默忽略"
        ),
        choices=("summary", "detail", "count_only"),
        required=False,
        allow_null=True,
        allow_blank=True,
        default=None,
    )
    order_by = serializers.ChoiceField(
        help_text=_(
            "排序键，缺省 total_size_mb。"
            "total_size_mb（找大表，最常见入口）；"
            "row_count（按行数排序）；"
            "index_size_mb（找索引膨胀的表）；"
            "stats_outdated_count（找统计过期最严重的表，UPDATE STATISTICS 候选）；"
            "last_user_update（按写入活跃度排序，desc=最近被写、asc=最久未被写）。"
            "注意：summary 模式只返回 4 个 L1 字段，若按非 L1 字段排序，明细里看不到该字段值，"
            "如需查看请用 verbose=detail；verbose=count_only 时此参数被忽略"
        ),
        choices=_ALLOWED_ORDER_BY_CHOICES,
        required=False,
        allow_null=True,
        allow_blank=True,
        default=None,
    )
    order = serializers.ChoiceField(
        help_text=_("排序方向，desc（默认）或 asc；非法值容错回落到 desc；verbose=count_only 时此参数被忽略"),
        choices=_ALLOWED_ORDER_CHOICES,
        required=False,
        allow_null=True,
        allow_blank=True,
        default=None,
    )


class _TableStatusItemSerializer(serializers.Serializer):
    """表状态明细元素。

    summary 模式下仅 schema_name / table_name / row_count / total_size_mb 必现；
    其余字段仅在 detail 模式下出现，因此统一标 required=False。
    """

    # ---- L1：summary / detail 都会出现 ----
    schema_name = serializers.CharField(help_text=_("schema 名"))
    table_name = serializers.CharField(help_text=_("表名"))
    row_count = serializers.IntegerField(
        help_text=_("行数（来自 sys.dm_db_partition_stats 的近似值）"),
        required=False,
    )
    total_size_mb = serializers.IntegerField(
        help_text=_("总占用空间 MB（含数据 + 索引 + LOB + 行溢出）"),
        required=False,
    )

    # ---- L2 / L3 / L4：仅 detail 模式才会出现 ----
    object_id = serializers.IntegerField(help_text=_("表对象 ID"), required=False)

    create_date = serializers.CharField(help_text=_("表创建时间"), required=False, allow_null=True, allow_blank=True)
    modify_date = serializers.CharField(help_text=_("表最近一次 DDL 时间"), required=False, allow_null=True, allow_blank=True)

    is_heap = serializers.IntegerField(help_text=_("是否为堆表 1/0（无聚集索引）"), required=False)
    index_count = serializers.IntegerField(help_text=_("非堆索引数量（含聚集 + 非聚集）"), required=False)
    partition_count = serializers.IntegerField(help_text=_("分区数量；非分区表为 1"), required=False)
    has_primary_key = serializers.IntegerField(help_text=_("是否存在主键 1/0"), required=False)

    data_size_mb = serializers.IntegerField(help_text=_("数据空间 MB（含 LOB / row-overflow）"), required=False)
    index_size_mb = serializers.IntegerField(help_text=_("非聚集索引空间 MB"), required=False)

    last_user_seek = serializers.CharField(
        help_text=_("索引最近一次 user_seek 时间"), required=False, allow_null=True, allow_blank=True
    )
    last_user_scan = serializers.CharField(
        help_text=_("索引最近一次 user_scan 时间"), required=False, allow_null=True, allow_blank=True
    )
    last_user_lookup = serializers.CharField(
        help_text=_("索引最近一次 user_lookup 时间"), required=False, allow_null=True, allow_blank=True
    )
    last_user_update = serializers.CharField(
        help_text=_("索引最近一次 user_update 时间"), required=False, allow_null=True, allow_blank=True
    )

    total_modification_counter = serializers.IntegerField(
        help_text=_("该表所有索引/统计累计的未消化修改次数总和（来自 sys.sysindexes.rowmodctr）"),
        required=False,
    )
    stats_outdated_count = serializers.IntegerField(
        help_text=_(
            "该表上『统计画像可能过期』的统计对象数量（基于经验阈值判定，数据源同上）。"
            ">0 时，建议优先执行 UPDATE STATISTICS（轻量、不阻塞业务），"
            "而不是 ALTER INDEX REBUILD；后者请结合 get_index_fragmentation 的碎片率独立判断。"
        ),
        required=False,
    )


class SQLServerListTableStatusOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(help_text=_("实际查询的实例地址"))
    role = serializers.CharField(help_text=_("查询实例的角色"))
    dbname = serializers.CharField(help_text=_("目标业务库名"))
    schema_filter = serializers.CharField(
        help_text=_("传入的 schema 过滤值；为空表示未过滤"),
        allow_null=True,
        allow_blank=True,
    )
    table_filter = serializers.CharField(
        help_text=_("传入的 table_name 精确过滤值；为空表示未按表名过滤"),
        allow_null=True,
        allow_blank=True,
    )
    limit = serializers.IntegerField(help_text=_("实际生效的 limit；verbose=count_only 时为 0"))
    table_count = serializers.IntegerField(help_text=_("本次返回的明细条数；verbose=count_only 时为 0"))
    verbose = serializers.CharField(
        help_text=_("实际生效的输出粒度：summary / detail / count_only"),
    )
    total_user_table_count = serializers.IntegerField(
        help_text=_("当前库（叠加 schema/table_name 过滤后）的用户表总数；" "仅 verbose=count_only 时填充实际值，其他模式为 null"),
        allow_null=True,
    )
    order_by = serializers.CharField(
        help_text=_("实际生效的排序键；verbose=count_only 时为 null"),
        allow_null=True,
        allow_blank=True,
    )
    order = serializers.CharField(
        help_text=_("实际生效的排序方向 desc/asc；verbose=count_only 时为 null"),
        allow_null=True,
        allow_blank=True,
    )
    tables = _TableStatusItemSerializer(many=True, help_text=_("表状态清单（按总大小倒序）"))
