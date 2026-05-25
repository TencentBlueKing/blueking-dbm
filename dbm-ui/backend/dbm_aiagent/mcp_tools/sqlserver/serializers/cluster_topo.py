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

from backend.dbm_aiagent.mcp_tools.mysql.serializers.cluster_topo import MySQLStorageInstanceSerializer


class SQLServerTopoInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))


class SQLServerTopoOutputSerializer(serializers.Serializer):
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    region = serializers.CharField(help_text=_("地域"))
    tolerance_level = serializers.IntegerField(help_text=_("容灾级别"))
    time_zone = serializers.CharField(help_text=_("时区"))
    sync_mode = serializers.CharField(help_text=_("数据同步模式, 仅 SQLServer_ha 有效"), required=False, default=None)
    storage = MySQLStorageInstanceSerializer(help_text=_("存储层实例信息"))


class SqlserverStorageInstanceSerializer(MySQLStorageInstanceSerializer):
    """
    sqlserver 实例返回格式
    """

    version = serializers.CharField(help_text=_("实例版本"))
