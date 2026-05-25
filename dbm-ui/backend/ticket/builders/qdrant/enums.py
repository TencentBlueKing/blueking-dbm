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

from enum import Enum


class QdrantOperationType(str, Enum):
    """Qdrant操作类型枚举"""

    CreateCluster = "CreateCluster"
    """创建集群"""

    DeleteCluster = "DeleteCluster"
    """删除集群"""

    UpdateCluster = "UpdateCluster"
    """更新集群"""

    PartialUpdateCluster = "PartialUpdateCluster"
    """局部更新集群"""

    StartCluster = "StartCluster"
    """启动集群"""

    StopCluster = "StopCluster"
    """停止集群"""

    RestartCluster = "RestartCluster"
    """重启集群"""

    StartComponent = "StartComponent"
    """启动组件"""

    StopComponent = "StopComponent"
    """停止组件"""

    RestartComponent = "RestartComponent"
    """重启组件"""

    VerticalScaling = "VerticalScaling"
    """垂直扩缩容"""

    HorizontalScaling = "HorizontalScaling"
    """水平扩缩容"""

    VolumeExpansion = "VolumeExpansion"
    """存储扩容"""

    UpgradeComp = "UpgradeComp"
    """升级组件"""

    ExposeService = "ExposeService"
    """暴露服务"""

    CreateK8sNamespace = "CreateK8sNamespace"
    """创建 K8s 命名空间"""

    DeleteK8sPod = "DeleteK8sPod"
    """删除 K8s Pod"""
