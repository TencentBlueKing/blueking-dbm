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


class MultiValueCharField(serializers.ListField):
    """
    支持多种格式的多值字符字段

    支持的格式:
    - CSV 格式: ?requestType=RestartCluster,CStopCluster
    - 多值格式: ?requestType=RestartCluster&requestType=CStopCluster
    """

    def to_internal_value(self, data):
        """处理 CSV 格式的字符串，将其转换为列表"""
        if isinstance(data, str):
            # 按逗号分割 CSV 格式
            data = [item.strip() for item in data.split(",") if item.strip()]
        return super().to_internal_value(data)


class ClusterOperationLogSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    limit = serializers.IntegerField(help_text=_("分页限制"), required=False, default=10)
    offset = serializers.IntegerField(help_text=_("分页起始"), required=False, default=0)
    k8sClusterName = serializers.CharField(help_text=_("k8s集群名称"))
    clusterName = serializers.CharField(help_text=_("集群名称"))
    namespace = serializers.CharField(help_text=_("命名空间"))
    creator = serializers.CharField(help_text=_("操作人"), required=False)
    requestType = MultiValueCharField(
        child=serializers.CharField(),
        help_text=_("操作类型"),
        required=False,
        allow_empty=True,
        default=list,
    )
    requestParams = serializers.CharField(help_text=_("操作内容"), required=False)
    startTime = serializers.CharField(help_text=_("开始时间"), required=False)
    endTime = serializers.CharField(help_text=_("结束时间"), required=False)


class KubernetesTopoGraphSerializer(serializers.Serializer):
    k8sClusterName = serializers.CharField(help_text=_("k8s集群名称"))
    namespace = serializers.CharField(help_text=_("命名空间"))


class KubernetesComponentSpecSerializer(serializers.Serializer):
    k8sClusterName = serializers.CharField(help_text=_("k8s集群名称"))
    namespace = serializers.CharField(help_text=_("命名空间"))
    clusterName = serializers.CharField(help_text=_("集群名称"))


class KubernetesRetrieveInstancesSerializer(serializers.Serializer):
    k8sClusterName = serializers.CharField(help_text=_("k8s集群名称"))
    namespace = serializers.CharField(help_text=_("命名空间"))
    clusterName = serializers.CharField(help_text=_("集群名称"))
    componentName = serializers.CharField(help_text=_("组件名称"))
    podName = serializers.CharField(help_text=_("组件实例名称"))
