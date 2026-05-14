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


class SQLServerWaitStatsSnapshotInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(
        help_text=_("实例地址 ip:port，可选；不传时缺省查询 master"),
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )
    top = serializers.IntegerField(
        help_text=_("返回条数上限，按累计等待时长倒序，取值范围 (0, 100]"),
        required=False,
        default=15,
        min_value=1,
        max_value=100,
    )


class SQLServerWaitStatsRowSerializer(serializers.Serializer):
    wait_type = serializers.CharField(help_text=_("等待类型"))
    waiting_tasks_count = serializers.IntegerField(help_text=_("发生等待的任务数"))
    wait_time_ms = serializers.IntegerField(help_text=_("累计等待时长 ms"))
    max_wait_time_ms = serializers.IntegerField(help_text=_("单次最长等待时长 ms"))
    signal_wait_time_ms = serializers.IntegerField(
        help_text=_("信号等待时长 ms，反映 CPU 调度压力"),
    )
    resource_wait_time_ms = serializers.IntegerField(
        help_text=_("资源等待时长 ms = wait_time_ms - signal_wait_time_ms"),
    )
    avg_wait_time_ms = serializers.IntegerField(help_text=_("平均单次等待时长 ms"))


class SQLServerWaitStatsSnapshotOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(help_text=_("实际查询的实例地址"))
    role = serializers.CharField(help_text=_("查询实例的角色"))
    wait_stats = SQLServerWaitStatsRowSerializer(
        many=True,
        help_text=_("等待事件 TOP N（已剔除良性等待）"),
    )
