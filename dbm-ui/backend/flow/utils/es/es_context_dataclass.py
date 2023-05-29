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
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass()
class EsActKwargs:
    """
    定义ES活动节点的私有变量dataclass类
    """

    bk_cloud_id: int  # 对应的云区域ID
    exec_ip: Optional[Any] = None  # 表示执行的IP，多个IP传入list，单个IP传入str，空传入None
    set_trans_data_dataclass: str = None  # 加载到上下文的dataclass类的名称
    get_es_payload_func: str = None  # 上下文中EsActPayload类的获取参数方法名称。空则传入None
    es_role: str = None  # 表示单据执行的节点角色
    instance_num: int = 1
    instance_name: str = "all"  # 实例名称
    file_list: list = field(default_factory=list)  # 传入文件传输节点的文件名称列表，默认空字典
    cluster: dict = field(default_factory=dict)  # 集群信息


@dataclass()
class EsApplyContext:
    """
    定义申请ES集群的上下文dataclass类
    """

    es_act_payload: Optional[Any] = None  # 代表获取es的payload参数的类
    new_hot_ips: list = None  # 代表在资源池分配到hot的ip列表
    new_cold_ips: list = None  # 代表在资源池分配到cold的ip列表
    new_master_ips: list = None  # 代表在资源池分配到master的ip列表
    new_client_ips: list = None  # 代表在资源池分配到client的ip列表

    @staticmethod
    def get_new_hot_ips_var_name() -> str:
        return "new_hot_ips"

    @staticmethod
    def get_new_cold_ips_var_name() -> str:
        return "new_cold_ips"

    @staticmethod
    def get_new_master_ips_var_name() -> str:
        return "new_master_ips"

    @staticmethod
    def get_new_client_ips_var_name() -> str:
        return "new_client_ips"


@dataclass()
class EsShrinkContext:
    """
    定义缩容ES集群的上下文dataclass类
    """

    es_act_payload: Optional[Any] = None  # 代表获取es的payload参数的类


@dataclass()
class DnsKwargs:
    """
    定义dns管理的活动节点专属参数
    """

    bk_cloud_id: int  # 操作的云区域id
    dns_op_type: Optional[Any]  # 操作的域名方式
    delete_cluster_id: int = None  # 操作的集群，回收集群时需要
    domain_name: str = None  # 如果添加域名时,添加域名名称
    dns_op_exec_port: int = None  # 如果做添加或者更新域名管理，执行实例的port
