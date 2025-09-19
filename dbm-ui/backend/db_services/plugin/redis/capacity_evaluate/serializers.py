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
from rest_framework import serializers


class ActionInfoSLZ(serializers.Serializer):
    """Action information serializer"""

    bk_biz_id = serializers.IntegerField(help_text="Business ID")
    action_id = serializers.CharField(max_length=50, help_text="Action ID")
    action_name = serializers.CharField(max_length=200, help_text="Action name")
    action_type = serializers.CharField(
        max_length=100, help_text="full or incr, default is incr", required=False, allow_blank=True
    )
    action_user = serializers.CharField(max_length=100, help_text="Action user", required=False)
    start_time = serializers.DateTimeField(help_text="Start time")
    end_time = serializers.DateTimeField(help_text="End time")
    is_force = serializers.IntegerField(min_value=0, max_value=1, help_text="Force flag")
    user = serializers.CharField(max_length=100, help_text="User", required=False)
    debug = serializers.IntegerField(min_value=0, max_value=1, help_text="Debug flag", required=False)


class ReqSLZ(serializers.Serializer):
    """Request requirements serializer"""

    cluster_domain = serializers.CharField(max_length=200, help_text="Redis cluster domain", required=True)
    req_capacity_m = serializers.IntegerField(min_value=0, default=0, help_text="Required capacity size in MB")
    req_capacity_g = serializers.IntegerField(min_value=0, default=0, help_text="Required capacity size in GB")
    req_qps_k = serializers.IntegerField(min_value=0, help_text="Required QPS in thousands", required=True)
    req_flag_no_big_key_with_a_lot_of_member = serializers.IntegerField(
        required=True, min_value=0, max_value=1, help_text="Flag for no big key with lots of members"
    )
    req_flag_no_big_value = serializers.IntegerField(
        required=True, min_value=0, max_value=1, help_text="Flag for no big value"
    )
    req_flag_no_big_result = serializers.IntegerField(
        required=True, min_value=0, max_value=1, help_text="Flag for no big result"
    )
    req_flag_no_hot_key = serializers.IntegerField(
        required=True, min_value=0, max_value=1, help_text="Flag for no hot key"
    )
    req_flag_no_use_dns = serializers.IntegerField(
        required=True, min_value=0, max_value=1, help_text="Flag for no use DNS"
    )
    key_pattern = serializers.ListField(
        required=False, child=serializers.CharField(max_length=100), help_text="Key patterns to evaluate"
    )


class CapacityEvaluateSLZ(serializers.Serializer):
    """Main capacity evaluation serializer"""

    action_info = ActionInfoSLZ(help_text="Action information", required=True)
    req = serializers.ListField(child=ReqSLZ(), help_text="List of capacity requirements", required=True)
