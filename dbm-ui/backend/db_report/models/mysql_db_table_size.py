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


class MysqlDbTableSize(models.Model):
    """MySQL库表容量统计表"""

    cluster_domain = models.CharField(max_length=200, help_text=_("集群域名"))
    dteventtimehour = models.DateTimeField(help_text=_("精确到小时的事件时间，用于查询、分组和过期"))
    report_time = models.CharField(max_length=32, null=True, help_text=_("上报时间"))
    thedate = models.IntegerField(help_text=_("日期"))
    dteventtimestamp = models.BigIntegerField(help_text=_("事件时间戳"))
    instance_host = models.CharField(max_length=60, null=True, help_text=_("实例主机"))
    instance_port = models.IntegerField(null=True, help_text=_("实例端口"))
    shard_value = models.IntegerField(null=True, help_text=_("分片值"))
    database_name = models.CharField(max_length=100, null=True, help_text=_("数据库名"))
    table_name = models.CharField(max_length=100, null=True, help_text=_("表名"))
    table_size = models.BigIntegerField(null=True, help_text=_("表大小"))
    original_database_name = models.CharField(max_length=100, null=True, help_text=_("原始数据库名"))
    database_size = models.BigIntegerField(null=True, help_text=_("数据库大小"))
    machine_type = models.CharField(max_length=60, null=True, help_text=_("机器类型"))
    instance_role = models.CharField(max_length=60, null=True, help_text=_("实例角色"))
    bk_biz_id = models.IntegerField(null=True, help_text=_("业务ID"))
    bk_cloud_id = models.IntegerField(null=True, help_text=_("云区域ID"))

    class Meta:
        # 表结构外部生成，这里只做查询
        managed = False
        app_label = "db_stats"
        db_table = "mysql_db_table_size"
        verbose_name = _("MySQL库表容量统计")
        verbose_name_plural = _("MySQL库表容量统计")

    def __str__(self):
        return (
            f"{self.cluster_domain}-{self.instance_host}:{self.instance_port}-"
            f"{self.database_name}.{self.table_name}"
        )
