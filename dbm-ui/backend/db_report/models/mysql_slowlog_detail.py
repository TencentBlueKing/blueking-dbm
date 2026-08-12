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


class MysqlSlowlogDetail(models.Model):
    """MySQL慢日志详情表"""

    cluster_domain = models.CharField(max_length=255, help_text=_("集群域名"))
    instance_role = models.CharField(max_length=60, null=True, help_text=_("实例角色"))
    query_digest_md5 = models.CharField(max_length=100, null=True, help_text=_("查询摘要MD5"))
    dteventtimehour = models.DateTimeField(help_text=_("精确到小时的事件时间，用于查询、分组和过期"))
    log_time = models.DateTimeField(help_text=_("日志时间"))
    dteventtimestamp = models.DateTimeField(help_text=_("事件时间戳"))
    thedate = models.IntegerField(help_text=_("日期"))
    instance_host = models.CharField(max_length=60, null=True, help_text=_("实例主机"))
    instance_port = models.IntegerField(null=True, help_text=_("实例端口"))
    query_time = models.FloatField(null=True, help_text=_("查询耗时"))
    lock_time = models.FloatField(null=True, help_text=_("锁等待时间"))
    rows_examined = models.IntegerField(null=True, help_text=_("扫描行数"))
    rows_sent = models.IntegerField(null=True, help_text=_("返回行数"))
    query_digest_text = models.CharField(max_length=8192, null=True, help_text=_("查询摘要文本"))
    query_string = models.TextField(null=True, help_text=_("完整查询语句"))
    query_length = models.IntegerField(null=True, help_text=_("查询长度"))
    query_command = models.CharField(max_length=30, null=True, help_text=_("查询命令类型"))
    query_db_name = models.CharField(max_length=100, null=True, help_text=_("查询数据库名"))
    db_name = models.CharField(max_length=100, null=True, help_text=_("数据库名"))
    table_names = models.CharField(max_length=255, null=True, help_text=_("表名"))
    session_id = models.IntegerField(null=True, help_text=_("会话ID 连接ID"))
    client_host = models.CharField(max_length=60, null=True, help_text=_("客户端主机"))
    username = models.CharField(max_length=60, null=True, help_text=_("用户名"))
    cluster_type = models.CharField(max_length=60, null=True, help_text=_("集群类型"))
    bk_cloud_id = models.IntegerField(null=True, help_text=_("云区域ID"))
    bk_biz_id = models.IntegerField(null=True, help_text=_("业务ID"))
    app_name = models.CharField(max_length=60, null=True, help_text=_("应用名称"))
    parse_failure = models.IntegerField(null=True, help_text=_("解析失败标记"))

    class Meta:
        # 表结构外部生成，这里只做查询
        managed = False
        app_label = "db_stats"
        db_table = "tb_mysql_slow_log"
        verbose_name = _("MySQL慢日志详情")
        verbose_name_plural = _("MySQL慢日志详情")

    def __str__(self):
        return f"{self.cluster_domain}-{self.instance_host}:{self.instance_port}-{self.log_time}"
