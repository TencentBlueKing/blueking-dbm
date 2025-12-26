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

from backend.db_meta.enums import ClusterType, InstanceRole, MachineType, TenDBClusterSpiderRole

mysql_cluster_type_choices = [
    (ClusterType.TenDBSingle.value, ClusterType.TenDBSingle.name),
    (ClusterType.TenDBHA.value, ClusterType.TenDBHA.name),
    (ClusterType.TenDBCluster.value, ClusterType.TenDBCluster.name),
]

mysql_machine_type_choices = [
    (MachineType.SINGLE.value, MachineType.SINGLE.name),
    (MachineType.BACKEND.value, MachineType.BACKEND.name),
    (MachineType.REMOTE.value, MachineType.REMOTE.name),
    (MachineType.SPIDER.value, MachineType.SPIDER.name),
]

mysql_instance_role_choices = [
    (InstanceRole.BACKEND_MASTER.value, InstanceRole.BACKEND_MASTER.name),
    (InstanceRole.BACKEND_SLAVE.value, InstanceRole.BACKEND_SLAVE.name),
    (InstanceRole.REMOTE_MASTER.value, InstanceRole.REMOTE_MASTER.name),
    (InstanceRole.REMOTE_SLAVE.value, InstanceRole.REMOTE_SLAVE.name),
    (TenDBClusterSpiderRole.SPIDER_MASTER, TenDBClusterSpiderRole.SPIDER_MASTER.name),
]
