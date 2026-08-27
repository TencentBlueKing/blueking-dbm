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

from backend.bk_web.constants import LEN_L_LONG, LEN_LONG, LEN_MIDDLE, LEN_NORMAL


class MysqlSqlFileExecDuration(models.Model):
    """
    SQL 导入：单个 SQL 文件在单个库上的执行总耗时。

    与 MysqlSqlExecDuration（单条 SQL 审计）分开。数据来自 dbactuator
    ExecuteSQLFileComp.OutputCtx，由 ExecuteDBActuatorScriptWithBkJobRecordService
    在作业成功后解析 <ctx> 入库。
    sql_file_path 为 BKRepo 对象路径（如 mysql/sqlfile/{biz}/foo.sql），不含 project/bucket。
    """

    ticket_id = models.PositiveIntegerField(_("单据ID"), db_index=True)
    cluster_id = models.PositiveIntegerField(_("集群ID"), db_index=True)
    cluster_domain = models.CharField(_("集群主域名"), max_length=255, blank=True, default="", db_index=True)
    db_name = models.CharField(_("数据库名"), max_length=LEN_MIDDLE, db_index=True)
    sql_file = models.CharField(_("SQL文件名"), max_length=LEN_LONG)
    sql_file_path = models.CharField(
        _("SQL文件制品库路径"),
        max_length=LEN_L_LONG,
        blank=True,
        default="",
        help_text=_("BKRepo 对象路径，如 mysql/sqlfile/{biz}/foo.sql，不含 project/bucket"),
    )
    duration_sec = models.IntegerField(_("执行耗时(秒)"))
    success = models.BooleanField(_("是否成功"), default=True)
    root_id = models.CharField(_("流程任务ID"), max_length=33, blank=True, default="", db_index=True)
    ip = models.CharField(_("执行IP"), max_length=LEN_NORMAL, blank=True, default="")
    port = models.IntegerField(_("执行端口"), null=True, blank=True)
    created_at = models.DateTimeField(_("创建时间"), auto_now_add=True, blank=True)

    class Meta:
        db_table = "tb_mysql_sql_file_exec_duration"
        unique_together = [("ticket_id", "cluster_id", "db_name", "sql_file")]
        verbose_name = _("MySQL SQL文件执行耗时")
        verbose_name_plural = _("MySQL SQL文件执行耗时")

    def __str__(self):
        return f"{self.ticket_id}-{self.cluster_id}-{self.db_name}-{self.sql_file}-{self.duration_sec}s"
