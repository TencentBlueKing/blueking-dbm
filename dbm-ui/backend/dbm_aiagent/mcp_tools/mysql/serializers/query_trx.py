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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class TrxRowSerializer(serializers.Serializer):
    trx_state = serializers.CharField(help_text=_("事务状态"))
    trx_started = serializers.CharField(help_text=_("事务开始时间"))
    trx_mysql_thread_id = serializers.CharField(help_text=_("事务关联的线程 ID"))
    id = serializers.CharField(help_text=_("连接 ID"))
    source_host = serializers.CharField(help_text=_("来源地址,tendbha集群这里显示的是 mysql-proxy 的 ip 地址"))
    command = serializers.CharField(help_text=_("正在执行的命令操作"))
    user = serializers.CharField(help_text=_("连接用户名"))
    db = serializers.CharField(help_text=_("正在访问的 db 名"))
    time = serializers.IntegerField(help_text=_("活跃时间, 单位是秒"))
    state = serializers.CharField(help_text=_("连接状态"))
    info = serializers.CharField(help_text=_("正在执行的 SQL 语句"), allow_null=True)


class QueryLongRunningTrxOutputSerializer(serializers.Serializer):
    long_running_trx = TrxRowSerializer(many=True, help_text=_("长事务列表"))
