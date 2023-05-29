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

from backend.db_meta.models import Cluster


def status_flag(cluster: Cluster) -> int:
    """
    集群状态详情
    返回的是 IntFlag, 具体定义在 backend/db_meta/enums/cluster_status.py::ClusterDBHAStatusFlags
    example:
    if ret & ClusterDBHAStatusFlags.ProxyUnavailable:
        print(ClusterDBHAStatusFlags.ProxyUnavailable.name)

    if ret & ClusterDBHAStatusFlags.ProxyUnavailable and ret & ClusterDBHAStatusFlags.MasterUnavailable:
        print("proxy and master down")

    由于主要是给代码能详细识别集群状态来控制是否能提单, 所以没有给人性化的可读字符串
    """
    return cluster.status_flag
