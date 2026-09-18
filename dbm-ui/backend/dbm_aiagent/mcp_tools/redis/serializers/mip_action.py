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


class ListMipActionsInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    action_id = serializers.CharField(help_text=_("Action ID"), required=False, allow_blank=True)
    cluster_domain = serializers.CharField(help_text=_("集群域名"), required=False, allow_blank=True)
    limit = serializers.IntegerField(help_text=_("返回条数上限"), required=False, default=50, min_value=1, max_value=200)


class MipActionRecordSerializer(serializers.Serializer):
    action_id = serializers.CharField(help_text=_("Action ID"))
    action_name = serializers.CharField(help_text=_("Action Name"))
    action_type = serializers.CharField(help_text=_("Action Type"))
    action_user = serializers.CharField(help_text=_("Action User"), allow_blank=True, allow_null=True, required=False)
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    bk_biz_name = serializers.CharField(help_text=_("业务名"), allow_blank=True, required=False)
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    cluster_type = serializers.CharField(help_text=_("集群类型"), allow_blank=True, required=False)
    evaluate_method = serializers.CharField(help_text=_("评估方法"), allow_blank=True, required=False)
    evaluate_time = serializers.DateTimeField(help_text=_("评估时间"), required=False)
    start_time = serializers.DateTimeField(help_text=_("开始时间"), required=False)
    end_time = serializers.DateTimeField(help_text=_("结束时间"), required=False)
    req_qps_k = serializers.IntegerField(help_text=_("需求 QPS(K)"))
    req_capacity_m = serializers.IntegerField(help_text=_("需求容量(MB)"))
    key_pattern = serializers.CharField(help_text=_("Key Pattern"), allow_blank=True, required=False)
    is_force = serializers.IntegerField(help_text=_("是否强制"), required=False)
    last_approved_user = serializers.CharField(help_text=_("最近审批人"), allow_blank=True, required=False)
    last_approved_status = serializers.IntegerField(help_text=_("最近审批状态"), required=False)
    last_approved_time = serializers.DateTimeField(help_text=_("最近审批时间"), required=False)


class ListMipActionsOutputSerializer(serializers.Serializer):
    count = serializers.IntegerField(help_text=_("记录数"))
    records = MipActionRecordSerializer(many=True, help_text=_("评估请求记录列表"))


class EvaluateMipActionInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    action_id = serializers.CharField(help_text=_("已提交的 Action ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名，可选，用于只评估某一集群"), required=False, allow_blank=True)
    is_force = serializers.IntegerField(help_text=_("强制评估标记，0/1；不传则用记录值"), required=False, min_value=0, max_value=1)


class EvaluateMipActionResultSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"), required=False, allow_blank=True)
    status = serializers.CharField(help_text=_("评估状态"))
    message = serializers.CharField(help_text=_("评估信息"), required=False, allow_blank=True)
    proxy_approve_ok = serializers.BooleanField(help_text=_("Proxy 评估是否通过"), required=False)
    proxy_approve_info = serializers.CharField(help_text=_("Proxy 评估详情"), required=False, allow_blank=True)
    backend_approve_ok = serializers.BooleanField(help_text=_("Backend 评估是否通过"), required=False)
    backend_approve_info = serializers.CharField(help_text=_("Backend 评估详情"), required=False, allow_blank=True)
    capacity_approve_ok = serializers.BooleanField(help_text=_("容量评估是否通过"), required=False)
    capacity_approve_info = serializers.CharField(help_text=_("容量评估详情"), required=False, allow_blank=True)
    time_elapsed_ms = serializers.IntegerField(help_text=_("耗时毫秒"), required=False)


class EvaluateMipActionOutputSerializer(serializers.Serializer):
    action_id = serializers.CharField(help_text=_("Action ID"))
    results = EvaluateMipActionResultSerializer(many=True, help_text=_("各集群评估结果"))


class GetSupportedQpsInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))


class GetSupportedQpsOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    supported_qps_k = serializers.FloatField(help_text=_("集群可支持总 QPS(K)，取 proxy/backend 较小值"))
    proxy_qps_k_total = serializers.FloatField(help_text=_("Proxy 可支持总 QPS(K)"))
    backend_qps_k_total = serializers.FloatField(help_text=_("Backend 可支持总 QPS(K)"))
    proxy_num = serializers.IntegerField(help_text=_("Proxy 数量"))
    shard_num = serializers.IntegerField(help_text=_("分片数量"))
    shard_spec = serializers.CharField(help_text=_("分片规格"), allow_blank=True, required=False)
    model = serializers.DictField(help_text=_("评估模型常量"))


class AnalyzeMipCapacityInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    current_time = serializers.CharField(
        help_text=_("当前时间（ISO），默认现在；用于筛选 end_time > current_time"),
        required=False,
        allow_blank=True,
    )
    stop_time = serializers.CharField(
        help_text=_("截止时间（ISO），可选；有则额外限制 start_time <= stop_time"),
        required=False,
        allow_blank=True,
    )


class ActiveMipActionSerializer(serializers.Serializer):
    action_id = serializers.CharField(help_text=_("Action ID"))
    action_name = serializers.CharField(help_text=_("Action Name"), allow_blank=True, required=False)
    action_user = serializers.CharField(help_text=_("Action User"), allow_blank=True, required=False)
    start_time = serializers.CharField(help_text=_("开始时间 ISO"), allow_null=True, required=False)
    end_time = serializers.CharField(help_text=_("结束时间 ISO"), allow_null=True, required=False)
    req_qps_k = serializers.IntegerField(help_text=_("需求 QPS(K)"))
    req_capacity_m = serializers.IntegerField(help_text=_("需求容量(MB)"), required=False)
    size_g = serializers.FloatField(help_text=_("需求容量(G)"), required=False)


class MipCapacitySummarySerializer(serializers.Serializer):
    count = serializers.IntegerField(help_text=_("记录数"))
    qps_peak = serializers.IntegerField(help_text=_("重叠窗口峰值 QPS(K)"))
    qps_peak_window = serializers.DictField(help_text=_("峰值时间窗 start_time/end_time"))
    qps_sum = serializers.IntegerField(help_text=_("QPS 简单求和(K)"))
    capacity_g_sum = serializers.FloatField(help_text=_("容量求和(G)"))
    note = serializers.CharField(help_text=_("说明"), required=False, allow_blank=True)


class LastEvaluateSerializer(serializers.Serializer):
    action_id = serializers.CharField(help_text=_("Action ID"), required=False, allow_blank=True)
    action_name = serializers.CharField(help_text=_("Action Name"), required=False, allow_blank=True)
    action_user = serializers.CharField(help_text=_("Action User"), required=False, allow_blank=True)
    approved_status = serializers.CharField(help_text=_("审批状态"), required=False, allow_blank=True)
    approved_comment = serializers.CharField(help_text=_("审批备注"), required=False, allow_blank=True)
    approved_user = serializers.CharField(help_text=_("审批人"), required=False, allow_blank=True)
    evaluate_time = serializers.CharField(help_text=_("评估时间 ISO"), required=False, allow_null=True)
    cluster_domain = serializers.CharField(help_text=_("集群域名"), required=False, allow_blank=True)
    proxy_count = serializers.IntegerField(help_text=_("Proxy 数量"), required=False)
    req_qps_k = serializers.IntegerField(help_text=_("本次需求 QPS(K)"), required=False)
    req_capacity_m = serializers.IntegerField(help_text=_("本次需求容量(MB)"), required=False)
    req_qps_k_total = serializers.IntegerField(help_text=_("同窗期总需求 QPS(K)"), required=False)
    req_capacity_m_total = serializers.IntegerField(help_text=_("同窗期总需求容量(MB)"), required=False)
    total_g = serializers.FloatField(help_text=_("总容量(G)"), required=False)
    free_g = serializers.FloatField(help_text=_("剩余容量(G)"), required=False)
    req_g = serializers.FloatField(help_text=_("总需求容量(G)"), required=False)
    not_finished_records_json = serializers.CharField(help_text=_("未结束记录 JSON"), required=False, allow_blank=True)


class ExpandSuggestSerializer(serializers.Serializer):
    suggest_type = serializers.CharField(help_text=_("建议类型"), required=False)
    cluster_domain = serializers.CharField(help_text=_("集群域名"), required=False, allow_blank=True)
    approved_status = serializers.CharField(help_text=_("审批状态"), required=False, allow_blank=True)
    proxy_count = serializers.IntegerField(help_text=_("当前 Proxy 数"), required=False)
    req_qps_k_total = serializers.FloatField(help_text=_("总需求 QPS(K)"), required=False)
    req_proxy_count = serializers.FloatField(help_text=_("需求 Proxy 数（按模型估算）"), required=False)
    proxy_count_diff = serializers.IntegerField(help_text=_("Proxy 差额"), required=False)
    total_g = serializers.FloatField(help_text=_("总容量(G)"), required=False)
    free_g = serializers.FloatField(help_text=_("剩余容量(G)"), required=False)
    req_g = serializers.FloatField(help_text=_("需求容量(G)"), required=False)
    need_capacity_g = serializers.IntegerField(help_text=_("需扩容量(G)"), required=False)
    need_proxy_count = serializers.IntegerField(help_text=_("需扩 Proxy 数"), required=False)
    need_capacity = serializers.IntegerField(help_text=_("需扩容量(G)，同 need_capacity_g"), required=False)


class AnalyzeMipCapacityOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    current_time = serializers.CharField(help_text=_("查询基准时间 ISO"))
    stop_time = serializers.CharField(help_text=_("截止时间 ISO"), allow_null=True, required=False)
    active_actions = ActiveMipActionSerializer(many=True, help_text=_("时间窗内未结束 Action"))
    active_summary = MipCapacitySummarySerializer(help_text=_("进行中 Action 汇总"))
    last_evaluate = LastEvaluateSerializer(help_text=_("最近一次评估"), allow_null=True, required=False)
    suggest = ExpandSuggestSerializer(help_text=_("扩容建议"), allow_null=True, required=False)
    related_actions = ActiveMipActionSerializer(many=True, help_text=_("history 同窗相关 Action"))
    related_summary = MipCapacitySummarySerializer(help_text=_("相关 Action 汇总"))


class GetClusterSpecInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))


class GetClusterSpecOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    storage_type = serializers.CharField(help_text=_("存储类型 memory/ssd 等"))
    proxy_num = serializers.IntegerField(help_text=_("Proxy 数量"))
    shard_num = serializers.IntegerField(help_text=_("分片数量"))
    proxy_spec = serializers.CharField(help_text=_("Proxy 规格串"), allow_blank=True)
    shard_spec = serializers.CharField(help_text=_("分片规格串"), allow_blank=True)
    proxy_cpu_total = serializers.FloatField(help_text=_("Proxy CPU 汇总（毫核折算）"), required=False)
    proxy_mem_total = serializers.FloatField(help_text=_("Proxy 内存汇总"), required=False)
    storage_cpu_total = serializers.FloatField(help_text=_("存储 CPU 汇总"), required=False)
    storage_mem_total_m = serializers.FloatField(help_text=_("存储内存汇总(MB)"), required=False)
    storage_disk_total = serializers.FloatField(help_text=_("存储磁盘汇总"), required=False)
    shard_cpu_core_m = serializers.FloatField(help_text=_("单分片 CPU（毫核）"), required=False)


class ListLastFailedClustersInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID；不传则 DBA 可查全业务"), required=False, allow_null=True)
    limit = serializers.IntegerField(help_text=_("返回条数上限"), required=False, default=100, min_value=1, max_value=500)


class LastFailedClusterRecordSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=False)
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=False)
    approved_status = serializers.CharField(help_text=_("最近评估状态 failed/error"))
    approved_comment = serializers.CharField(help_text=_("评估备注"), allow_blank=True, required=False)
    action_id = serializers.CharField(help_text=_("Action ID"), allow_blank=True, required=False)
    action_name = serializers.CharField(help_text=_("Action Name"), allow_blank=True, required=False)
    evaluate_time = serializers.CharField(help_text=_("评估时间 ISO"), allow_null=True, required=False)
    req_qps_k_total = serializers.IntegerField(help_text=_("同窗期总需求 QPS(K)"), required=False)
    req_capacity_m_total = serializers.IntegerField(help_text=_("同窗期总需求容量(MB)"), required=False)


class ListLastFailedClustersOutputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID；全业务查询时为 null"), allow_null=True, required=False)
    count = serializers.IntegerField(help_text=_("失败集群数"))
    cluster_domains = serializers.ListField(child=serializers.CharField(), help_text=_("最近一次评估失败的集群域名列表"))
    records = LastFailedClusterRecordSerializer(many=True, help_text=_("失败详情（含状态/备注）"))
