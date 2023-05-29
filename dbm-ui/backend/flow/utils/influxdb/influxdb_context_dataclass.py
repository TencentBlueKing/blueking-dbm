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
class ActKwargs:
    """
    定义活动节点的私有变量dataclass类
    """

    exec_ip: Optional[Any] = None  # 表示执行的ip，多个ip传入list类型，当个ip传入str类型，空则传入None
    bk_cloud_id: int = None  # 云区域ID
    set_trans_data_dataclass: str = None  # 加载到上下文的dataclass类的名称
    get_trans_data_ip_var: str = None  # 表示在上下文获取ip信息的变量名称。空则传入None
    get_kafka_payload_func: str = None  # 上下文中KafkaActPayload类的获取参数方法名称。空则传入None
    file_list: list = field(default_factory=list)  # 传入文件传输节点的文件名称列表，默认空字典
    is_update_trans_data: bool = False  # 表示是否合并上下文内容到单据cluster信息中，False表示不合并
    cluster: dict = field(default_factory=dict)  # 表示单据执行的集群信息，比如集群名称，集群域名等
    template: dict = field(default_factory=dict)  # 表示单据执行的集群信息，比如集群名称，集群域名等


@dataclass()
class DnsKwargs:
    """
    定义dns管理的活动节点专属参数
    """

    dns_op_type: Optional[Any]  # 操作的域名方式
    delete_cluster_id: int = None  # 操作的集群，回收集群时需要
    add_domain_name: str = None  # 如果添加域名时,添加域名名称
    dns_op_exec_port: int = None  # 如果做添加或者更新域名管理，执行实例的port


@dataclass()
class ApplyContext:
    """
    定义单节点申请的上下文dataclass类
    """

    new_ip: str = None  # 代表在资源池分配到的每个单节点集群的新的ip
    kafka_act_payload: Optional[Any] = None  # 代表获取kafka的payload参数的类
    new_broker_ips: list = None  # 代表在资源池分配到broker的ip列表
    new_zookeeper_ips: list = None  # 代表在资源池分配到zookeeper的ip列表

    @staticmethod
    def get_new_ip_var_name() -> str:
        """
        为了增加代码的可读性，同时手动输入字符串会有输入的风险，定义方法专门返回变量
        """
        return "new_ip"


@dataclass()
class HaApplyContext:
    """
    定义主从版申请的上下文dataclass类
    """

    new_master_ip: str = None  # 代表在资源池分配到的每套HA集群的新的master
    new_slave_ip: str = None  # 代表在资源池分配的每套HA集群的新的slave
    new_proxy_1_ip: str = None  # 代表在资源池分配的每套HA集群的新的proxy_1
    new_proxy_2_ip: str = None  # 代表在资源池分配的每套HA集群的新的proxy_2
    new_all_ips: list = field(default_factory=list)  # 代表在资源池这套集群分配到所有的ip
    new_proxy_ips: list = field(default_factory=list)  # 代表在资源池这套集群分配到所有的proxy_ip
    master_ip_sync_info: dict = field(default_factory=dict)  # 代表获取到master的主从复制位点信息
    mysql_act_payload: Optional[Any] = None  # 代表获取mysql的payload参数的类

    def get_all_ips(self):
        self.new_all_ips = [self.new_master_ip, self.new_slave_ip, self.new_proxy_1_ip, self.new_proxy_2_ip]

    def get_proxy_ips(self):
        self.new_proxy_ips = [self.new_proxy_1_ip, self.new_proxy_2_ip]

    @staticmethod
    def get_new_master_ip_var_name() -> str:
        return "new_master_ip"

    @staticmethod
    def get_new_slave_ip_var_name() -> str:
        return "new_slave_ip"

    @staticmethod
    def get_new_proxy_ips_var_list() -> list:
        return ["new_proxy_1_ip", "new_proxy_2_ip"]

    @staticmethod
    def get_new_all_ips_var_name() -> str:
        return "new_all_ips"

    @staticmethod
    def get_new_proxy_ips_var_name() -> str:
        return "new_proxy_ips"


@dataclass()
class ClusterDestroyContext:
    """
    定义集群下架的上下文dataclass类（包括主从版集群下架和单节点版下架）
    """

    mysql_act_payload: Optional[Any] = None  # 代表获取mysql的payload参数的类
