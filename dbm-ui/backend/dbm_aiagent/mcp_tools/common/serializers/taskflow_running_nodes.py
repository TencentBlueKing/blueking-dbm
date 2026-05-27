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


class TaskflowRunningNodesInputSerializer(serializers.Serializer):
    root_id = serializers.CharField(help_text=_("任务流 root_id"))
    worker_subprocess_id = serializers.CharField(
        help_text=_("主任务子流程ID，传入则只查该子流程下的节点；不传则查root_id下所有节点"),
        required=False,
        default=None,
        allow_null=True,
        allow_blank=True,
    )
    enable_historical_comparison = serializers.BooleanField(
        help_text=_("是否开启历史耗时对比（需同时传入cluster_ids）"),
        required=False,
        default=False,
    )
    cluster_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text=_("集群ID列表，开启历史对比时必传，用于查找同集群同类型单据的历史执行记录（一个单据可能涉及多个集群）"),
        required=False,
        default=None,
        allow_null=True,
    )


class HistoricalSampleSerializer(serializers.Serializer):
    root_id = serializers.CharField(help_text=_("历史流程root_id"))
    node_id = serializers.CharField(help_text=_("历史节点ID"))
    duration_seconds = serializers.IntegerField(help_text=_("历史节点耗时(秒)"))
    similarity = serializers.FloatField(help_text=_("入参相似度(0~1)"))
    ticket_id = serializers.IntegerField(help_text=_("历史单据ID"))


class HistoricalComparisonSerializer(serializers.Serializer):
    matched_sample_count = serializers.IntegerField(help_text=_("匹配到的有效历史样本数"))
    avg_duration_seconds = serializers.FloatField(help_text=_("历史平均耗时(秒)"), allow_null=True)
    max_duration_seconds = serializers.FloatField(help_text=_("历史最大耗时(秒)"), allow_null=True)
    min_duration_seconds = serializers.FloatField(help_text=_("历史最小耗时(秒)"), allow_null=True)
    matched_samples = HistoricalSampleSerializer(many=True, help_text=_("匹配到的历史样本详情"))


class RunningNodeSerializer(serializers.Serializer):
    node_id = serializers.CharField(help_text=_("节点ID"))
    node_name = serializers.CharField(help_text=_("节点名称"))
    started_at = serializers.CharField(help_text=_("节点开始执行时间(ISO格式)"), allow_null=True)
    duration_seconds = serializers.IntegerField(help_text=_("节点已运行时长(秒)"))
    component_code = serializers.CharField(help_text=_("组件代码"), required=False, allow_blank=True, default="")
    historical_comparison = HistoricalComparisonSerializer(
        help_text=_("历史耗时对比数据（仅enable_historical_comparison=True时返回）"),
        required=False,
        allow_null=True,
    )
    historical_comparison_error = serializers.CharField(
        help_text=_("历史对比未生效的原因（参数缺失或未匹配到样本时返回）"),
        required=False,
        allow_null=True,
        allow_blank=True,
        default=None,
    )


class TaskflowRunningNodesOutputSerializer(serializers.Serializer):
    root_id = serializers.CharField(help_text=_("流程root_id"))
    worker_subprocess_id = serializers.CharField(help_text=_("主任务子流程ID"), allow_null=True)
    flow_status = serializers.CharField(help_text=_("流程当前状态"))
    ticket_type = serializers.CharField(help_text=_("单据类型"))
    running_nodes = serializers.ListField(child=RunningNodeSerializer(), help_text=_("正在运行的节点列表"))
    total_running_count = serializers.IntegerField(help_text=_("正在运行的节点总数"))
