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
from typing import List, Union

from django.db.models import QuerySet

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, Machine
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpNotSupportClusterTypeException


def assert_cluster_type(
    check_obj: Union[Cluster, QuerySet[Cluster], Machine, ClusterType], allow_cluster_types: List[ClusterType]
) -> None:
    if isinstance(check_obj, Cluster):
        if check_obj.cluster_type not in allow_cluster_types:
            raise DBMMcpNotSupportClusterTypeException(cluster_type=check_obj.cluster_type)
    elif isinstance(check_obj, Machine):
        if check_obj.cluster_type not in allow_cluster_types:
            raise DBMMcpNotSupportClusterTypeException(cluster_type=check_obj.cluster_type)
    elif isinstance(check_obj, ClusterType):
        if check_obj not in allow_cluster_types:
            raise DBMMcpNotSupportClusterTypeException(cluster_type=check_obj)
    else:
        unsupported_clusters = check_obj.exclude(cluster_type__in=allow_cluster_types)
        if unsupported_clusters.exists():
            raise DBMMcpNotSupportClusterTypeException(
                cluster_type=set(unsupported_clusters.values_list("cluster_type", flat=True))
            )
