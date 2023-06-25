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
from typing import Optional, Any

from dataclasses import dataclass, field


@dataclass()
class RiakActKwargs:
    """
    定义Riak活动节点的私有变量dataclass类
    """

    bk_cloud_id: int  # 对应的云区域ID
    exec_ip: Optional[Any] = None  # 表示执行的IP，多个IP传入list，单个IP传入str，空传入None
    set_trans_data_dataclass: str = None  # 加载到上下文的dataclass类的名称
    get_riak_payload_func: str = None  # 上下文中RiakActPayload类的获取参数方法名称。空则传入None
    file_list: list = field(default_factory=list)  # 传入文件传输节点的文件名称列表，默认空字典
    cluster: dict = field(default_factory=dict)  # 集群信息
    run_as_system_user: str = None  # 表示执行job的api的操作用户, None 默认是用root用户


@dataclass()
class ApplyManualContext:
    """
    定义单节点申请的上下文dataclass类(手输ip模式)
    """

    nodes: list = field(default_factory=list)  # 手工输入的所有ip
    base_node: str = None  # 选取一个ip为操作节点
    operate_nodes: list = field(default_factory=list)  # 除base_node外的其他ip


@dataclass()
class AddNodeManualContext:
    """
    定义单节点申请的上下文dataclass类(手输ip模式)
    """

    base_node: str = None  # 选取集群中已存在的一个ip为操作节点
    operate_nodes: list = field(default_factory=list)  # 手工输入的所有ip
