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
from django.utils.translation import gettext as _
from rest_framework import serializers


class GetAddonVersionsSerializer(serializers.Serializer):
    addonType = serializers.CharField(help_text=_("存储类型"), required=True)

    class Meta:
        swagger_schema_fields = {
            "addonType": "surrealdb",
        }


class GetK8sClusterConfigSerializer(serializers.Serializer):
    isPublic = serializers.BooleanField(help_text=_("是否公有集群"), required=True)

    class Meta:
        swagger_schema_fields = {
            "isPublic": True,
        }


class GetAddonSpecPlanSerializer(serializers.Serializer):
    addonType = serializers.CharField(help_text=_("存储类型"), required=True)
    addonVersion = serializers.CharField(help_text=_("存储版本"), required=True)
    # addonTopology = serializers.CharField(help_text=_("存储拓扑"), required=False)

    class Meta:
        swagger_schema_fields = {
            "addonType": "surrealdb",
            "addonVersion": "1.0.0",
        }


class K8sOperateBaseSerializer(serializers.Serializer):
    k8sClusterName = serializers.CharField(help_text=_("k8s集群名称"))
    namespace = serializers.CharField(help_text=_("命名空间"))
    clusterName = serializers.CharField(help_text=_("集群名称"))
    bk_username = serializers.CharField(help_text=_("用户名"))
    async_to_dbm = serializers.BooleanField(required=False, default=False)


class KubernetesRestartSerializer(K8sOperateBaseSerializer):
    """组件重启序列化器"""

    restart = serializers.ListSerializer(child=serializers.JSONField(), help_text=_("组件列表"))


class KubernetesHscalingSerializer(K8sOperateBaseSerializer):
    """组件水平扩容序列化器"""

    horizontalScaling = serializers.ListSerializer(child=serializers.JSONField(), help_text=_("水平扩缩资源详情"))


class KubernetesVscalingSerializer(K8sOperateBaseSerializer):
    """组件垂直扩容 磁盘扩容 修改组件配置 序列化器"""

    componentList = serializers.ListSerializer(child=serializers.JSONField(), help_text=_("组件列表"))


class KubernetesDeletePodSerializer(K8sOperateBaseSerializer):
    """组件pod删除序列化器"""

    podName = serializers.CharField(help_text=_("组件实例名称"))


class KubernetesComponentConfigPodSerializer(K8sOperateBaseSerializer):
    componentName = serializers.CharField(help_text=_("组件名称"))


class KubernetesPodLogSerializer(K8sOperateBaseSerializer):
    componentName = serializers.CharField(help_text=_("组件名称"))
    podName = serializers.CharField(help_text=_("组件实例名称"))
    container = serializers.CharField(help_text=_("容器名称"))
    limit = serializers.IntegerField(help_text=_("分页限制"), required=False, default=10)
    offset = serializers.IntegerField(help_text=_("分页起始"), required=False, default=0)
