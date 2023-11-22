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

from backend.flow.consts import HdfsRoleEnum
from blue_krill.data_types.enum import EnumField, StructuredEnum


@dataclass()
class ActKwargs:
    """
    定义活动节点的私有变量dataclass类
    """

    bk_cloud_id: int  # 对应的云区域ID
    exec_ip: Optional[Any] = None  # 表示执行的ip，多个ip传入list类型，单个ip传入str类型，空则传入None
    set_trans_data_dataclass: str = None  # 加载到上下文的dataclass类的名称
    get_trans_data_ip_var: str = None  # 表示在上下文获取ip信息的变量名称。空则传入None
    get_hdfs_payload_func: str = None  # 上下文中HdfsActPayload类的获取参数方法名称。空则传入None
    file_list: list = field(default_factory=list)  # 传入文件传输节点的文件名称列表，默认空字典
    is_update_trans_data: bool = False  # 表示是否合并上下文内容到单据cluster信息中，False表示不合并
    hdfs_role: str = None  # 表示单据执行的节点角色
    cluster: dict = field(default_factory=dict)  # 集群信息
    transfer_target_ip: str = None


@dataclass()
class HdfsApplyContext:
    """
    定义hdfs集群申请的上下文dataclass类
    """

    nn1_ip: str = None
    nn2_ip: str = None
    # 预留, 为空
    nn3_ip: str = None

    nn_ips: list = field(default_factory=list)
    zk_ips: list = field(default_factory=list)
    jn_ips: list = field(default_factory=list)
    dn_ips: list = field(default_factory=list)

    # 扩容DN IP列表
    new_dn_ips: list = field(default_factory=list)

    # 代表在资源池这套集群分配到所有的ip
    all_ips: list = field(default_factory=list)

    master_ips: list = field(default_factory=list)

    # 所有IP及主机名映射
    all_ip_hosts: dict = field(default_factory=dict)
    # 代表获取hdfs的payload参数的类
    hdfs_act_payload: Optional[Any] = None

    @staticmethod
    def get_nn1_ip_var_name() -> str:
        return "nn1_ip"

    @staticmethod
    def get_nn2_ip_var_name() -> str:
        return "nn2_ip"

    @staticmethod
    def get_nn_ips_var_name() -> str:
        return "nn_ips"

    @staticmethod
    def get_dn_ips_var_name() -> str:
        return "dn_ips"

    @staticmethod
    def get_new_dn_ips_var_name() -> str:
        return "new_dn_ips"

    @staticmethod
    def get_zk_ips_var_name() -> str:
        return "zk_ips"

    @staticmethod
    def get_jn_ips_var_name() -> str:
        return "jn_ips"

    @staticmethod
    def get_all_ips_var_name() -> str:
        return "all_ips"

    @staticmethod
    def get_master_ips_var_name() -> str:
        return "master_ips"


@dataclass()
class HdfsReplaceContext:
    """
    定义hdfs集群 替换节点的上下文dataclass类
    """

    cur_nn1_ip: str = None
    cur_nn2_ip: str = None
    cur_zk_ips: list = field(default_factory=list)
    cur_jn_ips: list = field(default_factory=list)
    cur_dn_ips: list = field(default_factory=list)
    cur_all_ips: list = field(default_factory=list)

    new_dn_ips: list = field(default_factory=list)
    new_master_ips: list = field(default_factory=list)

    cur_exec_ips: list = field(default_factory=list)
    new_ip: str = None
    old_ip: str = None

    # 所有IP及主机名映射
    cur_all_ip_hosts: dict = field(default_factory=dict)
    # 代表获取hdfs的payload参数的类
    hdfs_act_payload: Optional[Any] = None

    # generate_key 回写key info
    generate_key_info: dict = field(default_factory=dict)

    # check_active 回写主备节点 信息
    cluster_active_info: dict = field(default_factory=dict)
    cur_active_nn_ip: str = None
    cur_standby_nn_ip: str = None

    @staticmethod
    def get_nn1_ip_var_name() -> str:
        return "cur_nn1_ip"

    @staticmethod
    def get_nn2_ip_var_name() -> str:
        return "cur_nn2_ip"

    @staticmethod
    def get_nn_ips_var_name() -> str:
        return "cur_nn_ips"

    @staticmethod
    def get_dn_ips_var_name() -> str:
        return "cur_dn_ips"

    @staticmethod
    def get_zk_ips_var_name() -> str:
        return "cur_zk_ips"

    @staticmethod
    def get_jn_ips_var_name() -> str:
        return "cur_jn_ips"

    @staticmethod
    def get_all_ips_var_name() -> str:
        return "cur_all_ips"

    @staticmethod
    def get_new_dn_ips_var_name() -> str:
        return "new_dn_ips"

    @staticmethod
    def get_new_master_ips_var_name() -> str:
        return "new_master_ips"

    @staticmethod
    def get_cur_active_ip_var_name() -> str:
        return "cur_active_nn_ip"

    @staticmethod
    def get_cur_standby_ip_var_name() -> str:
        return "cur_standby_nn_ip"


@dataclass()
class HdfsReplaceKwargs:
    """
    定义替换流程 更新 当前集群IP的活动节点专属参数
    """

    role: HdfsRoleEnum = None
    old_ip: str = None  # 被替换的IP
    new_ip: str = None  # 新加入的IP


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


class UpdateDfsHostOperation(str, StructuredEnum):
    Add = EnumField("add", "add")
    Remove = EnumField("remove", "remove")
