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


class ResetDtsTaskSerializer(serializers.Serializer):
    """Reset DTS 任务：删除后按原配置重建并启动，使任务从 Dump 重跑；不会清理目标业务数据。"""

    task_name = serializers.CharField(help_text=_("DTS 任务名。reset 会删除并重建任务（从 Dump 重跑），不会清理目标业务数据。"))
    dts_cluster_id = serializers.IntegerField(help_text=_("DTS 集群 ID，用于解析 master_addr"))
