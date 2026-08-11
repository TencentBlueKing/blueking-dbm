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


class MysqlProxyConnlog(models.Model):
    """MySQL Proxy 连接日志"""

    cluster_domain = models.CharField(max_length=200, help_text=_("集群域名"))
    dteventtimehour = models.DateTimeField(help_text=_("精确到小时的事件时间"))
    thedate = models.IntegerField(help_text=_("日期"))
    dteventtimestamp = models.DateTimeField(help_text=_("事件时间戳"))
    instance_host = models.CharField(max_length=60, help_text=_("mysql-proxy ip"))
    instance_port = models.IntegerField(help_text=_("mysql-proxy port"))
    conn_time = models.DateTimeField(help_text=_("连接时间"))
    client_ip = models.CharField(max_length=60, null=True, help_text=_("客户端IP"))
    conn_user = models.CharField(max_length=100, null=True, help_text=_("连接用户"))
    session_id = models.IntegerField(null=True, help_text=_("连接会话ID"))
    bk_biz_id = models.IntegerField(null=True, help_text=_("业务ID"))
    bk_cloud_id = models.IntegerField(null=True, help_text=_("云区域ID"))

    class Meta:
        managed = False
        app_label = "db_stats"
        db_table = "mysql_proxy_connlog"
        verbose_name = _("MySQL Proxy连接日志")
        verbose_name_plural = _("MySQL Proxy连接日志")

    def __str__(self):
        return f"{self.cluster_domain}-{self.instance_host}-{self.conn_user}-{self.conn_time}"
