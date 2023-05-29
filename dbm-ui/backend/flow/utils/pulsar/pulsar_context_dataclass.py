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

from backend.flow.consts import MediumFileTypeEnum


@dataclass()
class PulsarActKwargs:
    """
    定义Pulsar活动节点的私有变量dataclass类
    """

    bk_cloud_id: int  # 操作的云区域id
    exec_ip: Optional[Any] = None  # 表示执行的IP，多个IP传入list，单个IP传入str，空传入None
    set_trans_data_dataclass: str = None  # 加载到上下文的dataclass类的名称
    get_trans_data_ip_var: str = None  # 表示在上下文获取ip信息的变量名称。空则传入None
    get_pulsar_payload_func: str = None  # 上下文中EsActPayload类的获取参数方法名称。空则传入None

    file_list: list = field(default_factory=list)  # 传入文件传输节点的文件名称列表，默认空字典
    cluster: dict = field(default_factory=dict)  # 集群信息
    role: str = None  # pulsar集群角色(zookeeper/bookkeeper/broker)
    zk_my_id: int = 0  # pulsar集群ZK 实例ID
    cur_bookie_num: int = 0  # pulsar当前bookie节点个数
    zk_host_map: dict = field(default_factory=dict)  # 替换ZK时使用，ZK IP域名映射


@dataclass()
class PulsarApplyContext:
    """
    定义申请Pulsar集群的上下文dataclass类
    """

    pulsar_act_payload: Optional[Any] = None  # 代表获取pulsar的payload参数的类
    new_broker_ips: list = None  # 代表在资源池分配到broker的ip列表
    new_bookie_ips: list = None  # 代表在资源池分配到bookkeeper的ip列表
    new_zk_ips: list = None  # 代表在资源池分配到zookeeper的ip列表
    # init_token_info 初始化集群返回token info
    init_token_info: dict = field(default_factory=dict)
    # schedule_count 缩容时等待次数统计
    schedule_count: int = 0

    @staticmethod
    def get_new_token_var_name() -> str:
        return "init_token_info"

    @staticmethod
    def get_new_broker_ips_var_name() -> str:
        return "new_broker_ips"

    @staticmethod
    def get_new_bookie_ips_var_name() -> str:
        return "new_bookie_ips"

    @staticmethod
    def get_new_zk_ips_var_name() -> str:
        return "new_zk_ips"


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


@dataclass()
class ZkDnsKwargs(DnsKwargs):
    zk_host_map: dict = field(default_factory=dict)
    old_zk_ip: str = None
    new_zk_ip: str = None


@dataclass()
class TransFilesKwargs:
    """
    定义文件传输的活动节点的专属参数
    """

    file_type: Optional[MediumFileTypeEnum]  # 源文件存储模式
    source_ip_list: list = field(default_factory=list)  # 源文件的机器IP列表，当file_type为服务器文件 时 需要传入
    file_target_path: str = None  # 目标IP文件路径
