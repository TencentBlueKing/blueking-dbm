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

from backend.db_meta.enums import InstanceRole, MachineType
from backend.dbm_aiagent.mcp_tools.mysql.serializers.usefully_choices import mysql_cluster_type_choices


class ShowProcessListInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_type = serializers.ChoiceField(choices=mysql_cluster_type_choices, help_text=_("集群类型"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    # addresses = serializers.ListField(child=serializers.CharField(), default=None, help_text=_("ip:port 形式的实例列表"))


class MySQLProcessSerializer(serializers.Serializer):
    host = serializers.CharField(help_text=_("ip:port 形式的来源地址"))
    command = serializers.CharField(help_text=_("正在执行的命令操作"))
    user = serializers.CharField(help_text=_("连接用户名"))
    db = serializers.CharField(help_text=_("正在访问的 db 名"))
    time = serializers.CharField(help_text=_("活跃时间, 单位是秒"))
    state = serializers.CharField(help_text=_("连接状态"))


class InstanceProcessListOutputSerializer(serializers.Serializer):
    address = serializers.CharField(help_text=_("ip:port 形式的实例地址"))
    process_list = serializers.ListField(child=MySQLProcessSerializer(), help_text=_("连接列表"))
    machine_type = serializers.ChoiceField(choices=MachineType.get_choices(), help_text=_("实例的机器类型"))
    instance_role = serializers.ChoiceField(choices=InstanceRole.get_choices(), help_text=_("实例角色"))


class ShowProcessListOutputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_type = serializers.ChoiceField(choices=mysql_cluster_type_choices, help_text=_("集群类型"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    cluster_process_lists = serializers.ListField(child=InstanceProcessListOutputSerializer(), help_text=_("集群连接信息"))
