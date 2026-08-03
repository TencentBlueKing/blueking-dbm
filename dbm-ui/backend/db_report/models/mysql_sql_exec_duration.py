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
from django.db import models
from django.utils.translation import gettext_lazy as _


class MysqlSqlExecDuration(models.Model):
    """
    MySQL SQL 执行耗时审计表

    刻意避开 "slow" 关键字，避免与 mysql 自身慢查询日志的镜像表 MysqlSlowlogDetail 混淆。
    本表记录的是 dbactuator 在执行 SQL 文件时单条 SQL 的真实耗时审计，与 mysql slow log 无关。

    数据流：
        dbactuator stdout marker
        -> 作业平台 log_content
        -> backend.flow.utils.job_log_parser.parse_sql_logs_by_ip()
        -> 过滤 duration_sec >= 60s
        -> backend.flow.utils.sql_exec_duration_recorder.record_sql_exec_durations(_by_ticket)()
        -> 入库本表

    冗余字段说明：
        cluster_domain 与 cluster_id 同时存在 —— 方便后续 enrich 路径直接拿域名查
        backend.db_report.models.MysqlDbTableSize 拿表/库容量；同时报告 / API 展示对人友好。

    字段填充时机：
        - sql_type / table_name：入库时调 SQLSimulationApi.parse_sql_tables，从
          ParseIncludeTableBase.command / table_name 提取。
        - table_size：
            * 普通表级 DDL/DML：按 (cluster_domain, database_name, table_name) 查
              MysqlDbTableSize，同小时 Sum（TenDBCluster 跨分片加总），多表再求和；
            * drop_db：填逻辑库 database_size（分片按 original_database_name 求和）；
            * call / 过程函数触发器事件：不查 size，置 NULL。
        - instance_role 默认 slave，无数据回退 orphan/master。
    """

    cluster_id = models.PositiveIntegerField(null=True, blank=True, db_index=True, help_text=_("集群ID"))
    cluster_domain = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
        help_text=_("集群主域名（冗余字段，从 db_meta.Cluster.immute_domain 取）"),
    )
    ticket_id = models.PositiveIntegerField(null=True, blank=True, db_index=True, help_text=_("单据ID"))
    root_id = models.CharField(max_length=33, db_index=True, help_text=_("流程任务ID"))
    job_instance_id = models.BigIntegerField(db_index=True, help_text=_("蓝鲸作业实例ID"))
    step_instance_id = models.BigIntegerField(null=True, blank=True, help_text=_("蓝鲸步骤实例ID"))
    ip = models.CharField(max_length=64, db_index=True, help_text=_("执行IP"))
    bk_cloud_id = models.IntegerField(default=0, help_text=_("云区域ID"))
    db_name = models.CharField(
        max_length=128,
        blank=True,
        default="",
        db_index=True,
        help_text=_("数据库名（来自 USE 语句或 dbactuator marker）"),
    )
    table_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("表名（来自 SQL 解析 API，多表逗号拼接；drop_db 等场景可为空）"),
    )
    sql_text = models.TextField(help_text=_("SQL 完整内容"))
    sql_type = models.CharField(
        max_length=32,
        blank=True,
        default="",
        db_index=True,
        help_text=_("SQL 语句类型（来自解析 API 的 command，如 update/delete/alter_table/drop_db）"),
    )
    sql_checksum = models.CharField(
        max_length=32,
        db_index=True,
        help_text=_("md5(sql_text) 的 32 位十六进制，用作去重唯一键的一部分"),
    )
    table_size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text=_("大小，单位字节。表级 SQL 为涉及表 size 之和；drop_db 为逻辑库 database_size；" "call/过程函数等不查 size 时为 NULL"),
    )
    duration_sec = models.FloatField(db_index=True, help_text=_("单条 SQL 执行耗时（秒）"))
    created_at = models.DateTimeField(auto_now_add=True, help_text=_("创建时间"))

    class Meta:
        db_table = "tb_mysql_sql_exec_duration"
        unique_together = [("root_id", "job_instance_id", "ip", "sql_checksum")]
        indexes = [
            models.Index(fields=["cluster_id", "created_at"]),
            models.Index(fields=["ticket_id", "root_id"]),
        ]
        verbose_name = _("MySQL SQL 执行耗时")
        verbose_name_plural = _("MySQL SQL 执行耗时")

    def __str__(self):
        return f"{self.cluster_domain or self.cluster_id}-{self.ip}-{self.duration_sec}s"
