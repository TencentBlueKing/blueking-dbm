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

from dataclasses import dataclass
from typing import Any, Optional


@dataclass()
class K8sSurrealDBActKwargs:
    """
    定义 surrealdb 单机版活动节点的私有变量dataclass类
    """

    bk_cloud_id: int
    set_trans_data_dataclass: str = None  # 加载到上下文的dataclass类的名称


@dataclass()
class K8sSurrealDBApplyContext:
    """
    定义 surrealdb 单机版申请的上下文数据类
    """

    clb_id: Optional[int] = None
    region_code: Optional[str] = None
    region_name: Optional[str] = None
    domain: Optional[str] = None
    vpc_id: Optional[str] = None
    clb_detail: Optional[dict] = None
    cluster_id: Optional[int] = None
    namespace: Optional[str] = None
    k8s_cluster_name: Optional[str] = None
    cluster_name: Optional[str] = None


@dataclass()
class DnsKwargs:
    """
    定义 dns 管理的活动节点专属参数
    """

    bk_cloud_id: int  # 操作的云区域id
    dns_op_type: Optional[Any]  # 操作的域名方式
    delete_cluster_id: int = None  # 操作的集群，回收集群时需要
    domain_name: str = None  # 如果添加域名时,添加域名名称
    dns_op_exec_port: int = None  # 如果做添加或者更新域名管理，执行实例的 port
