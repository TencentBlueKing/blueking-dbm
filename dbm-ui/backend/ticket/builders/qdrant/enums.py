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

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class QdrantOperationType(StrStructuredEnum):
    """Qdrant操作类型枚举"""

    CreateCluster = EnumField("CreateCluster", _("创建集群"))
    DeleteCluster = EnumField("DeleteCluster", _("删除集群"))
    UpdateCluster = EnumField("UpdateCluster", _("更新集群"))
    PartialUpdateCluster = EnumField("PartialUpdateCluster", _("局部更新集群"))
    StartCluster = EnumField("StartCluster", _("启动集群"))
    StopCluster = EnumField("StopCluster", _("停止集群"))
    RestartCluster = EnumField("RestartCluster", _("重启集群"))
    StartComponent = EnumField("StartComponent", _("启动组件"))
    StopComponent = EnumField("StopComponent", _("停止组件"))
    RestartComponent = EnumField("RestartComponent", _("重启组件"))
    VerticalScaling = EnumField("VerticalScaling", _("垂直扩缩容"))
    HorizontalScaling = EnumField("HorizontalScaling", _("水平扩缩容"))
    VolumeExpansion = EnumField("VolumeExpansion", _("存储扩容"))
    UpgradeComp = EnumField("UpgradeComp", _("升级组件"))
    ExposeService = EnumField("ExposeService", _("暴露服务"))
    CreateK8sNamespace = EnumField("CreateK8sNamespace", _("创建 K8s 命名空间"))
    DeleteK8sPod = EnumField("DeleteK8sPod", _("删除 K8s Pod"))
