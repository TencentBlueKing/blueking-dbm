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


class UpdateMachineSpecInputSerializer(serializers.Serializer):
    """
    Update machine spec configuration.
    更新机器规格配置。
    """

    ip_list = serializers.ListField(
        child=serializers.IPAddressField(),
        help_text=_(
            "List of machine IPs to update (max 100). "
            "机器 IP 列表，最多 100 个。"
            "Can be obtained from cluster topology or machine list queries. "
            "可从集群拓扑或机器列表查询获取。"
        ),
        max_length=100,
    )
    spec_id = serializers.IntegerField(
        help_text=_("Target spec ID to apply. " "目标规格 ID。" "Obtain from resource pool spec list. " "可从资源池规格列表获取。")
    )
    bk_cloud_id = serializers.IntegerField(
        help_text=_("Cloud area ID (default: 0 for direct connection). " "云区域 ID，默认 0 表示直连区域。"),
        default=0,
        required=False,
    )
    force = serializers.BooleanField(
        help_text=_(
            "Force overwrite existing spec (default: False). "
            "是否强制覆盖已有规格，默认 False。"
            "When False, only machines with empty spec_config can be updated. "
            "为 False 时，只能更新空规格的机器。"
        ),
        default=False,
        required=False,
    )


class FailedMachineSerializer(serializers.Serializer):
    """
    Failed machine update detail.
    更新失败的机器详情。
    """

    ip = serializers.CharField(help_text=_("Machine IP. 机器 IP。"))
    reason = serializers.CharField(help_text=_("Failure reason. 失败原因。"))


class UpdateMachineSpecOutputSerializer(serializers.Serializer):
    """
    Update machine spec response.
    更新机器规格响应。
    """

    success_count = serializers.IntegerField(help_text=_("Number of successfully updated machines. 成功更新的机器数量。"))
    failed_list = serializers.ListField(
        child=FailedMachineSerializer(),
        help_text=_(
            "List of failed updates with reason. "
            "更新失败的列表及原因。"
            "Format: [{'ip': '127.0.0.1', 'reason': 'machine not found'}]"
        ),
    )
