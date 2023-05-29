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
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_services.dbbase.constants import IpSource


class QuerySpecSLZ(serializers.Serializer):
    db_type = serializers.ChoiceField(required=False, choices=DBType.get_choices())


class CitySLZ(serializers.Serializer):
    """服务器区域信息"""

    city_code = serializers.CharField()
    city_name = serializers.CharField()
    # 库存信息
    inventory = serializers.IntegerField()
    inventory_tag = serializers.CharField()


class HostSpecSLZ(serializers.Serializer):
    """服务器规格"""

    type = serializers.CharField()
    spec = serializers.CharField()
    cpu = serializers.CharField()
    mem = serializers.CharField()


class CapSpecSLZ(serializers.Serializer):
    """申请容量"""

    cap_key = serializers.CharField()
    total_memory = serializers.CharField()
    maxmemory = serializers.FloatField()
    total_disk = serializers.CharField()
    max_disk = serializers.FloatField()
    shard_num = serializers.IntegerField()
    group_num = serializers.IntegerField()
    selected = serializers.BooleanField()


class QueryCapSpecSLZ(serializers.Serializer):
    ip_source = serializers.ChoiceField(help_text=_("主机来源"), choices=IpSource.get_choices())
    nodes = serializers.JSONField(help_text=_("部署节点"))
    cluster_type = serializers.ChoiceField(choices=ClusterType.get_choices(), required=False)
