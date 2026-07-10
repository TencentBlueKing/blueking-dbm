# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像 SDK 对外统一导出入口。

外部（各巡检维度开发者）**只应通过本 __init__ 引用 SDK 与所属 DB 的维度枚举**，示例::

    from datetime import datetime
    from backend.configuration.constants import DBType
    from backend.db_report.portrait import (
        MysqlPortraitDimensionCode,
        ingest_summary
    )

    ingest_summary(
        db_type=DBType.MySQL,
        dimension=MysqlPortraitDimensionCode.SLOW_QUERY,
        bk_biz_id=100001,
        cluster_domain="a.b.c.example.com",
        report_time=datetime.now(),
        summary="近 24h 慢日志同比 +32%，Top1 SQL 未走索引",
        detail_url="https://xxx/mysql/slowlog/detail?xxx"
    )

设计要点：
    - 对外仅暴露 **SDK 入口 + 各 DB 独立的维度枚举类**
    - 每个 DB 的枚举命名空间完全隔离；新增 DB 只需新建一个 ``xxx_dimensions.py``
      并在此文件添加对应 ``from ... import`` 行
    - 异常处理：如需捕获 SDK 异常，请 ``from backend.db_report.portrait.exceptions import ...``
"""
# 各 DB 的独立维度枚举（新增 DB 时在下方追加一行导入 + 补充 __all__）
from backend.db_report.portrait.mysql_dimensions import MysqlPortraitDimensionCode
from backend.db_report.portrait.redis_dimensions import RedisPortraitDimensionCode
from backend.db_report.portrait.sdk import ingest_summary

__all__ = [
    "ingest_summary",
    # 各 DB 维度枚举
    "MysqlPortraitDimensionCode",
    "RedisPortraitDimensionCode",
]
