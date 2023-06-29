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

"""
定义每个活动节点的私用变量kwargs的dataclass类型
建议每个活动节点都需要定义，这样可以知道每个活动节点需要的私有变量的结构体都可以知道
todo 后续慢慢定义好目前存量的活动节点的私有变量kwargs，调整所有单据入参方式
todo 结合validator来对dataclass对数据校验
"""


@dataclass()
class ExecActuatorBaseKwargs:
    """
    定义执行riak_db_actuator_executor活动节点的私用变量通用结构体
    """

    bk_cloud_id: int  # 对应的云区域ID
    run_as_system_user: str = None  # 表示执行job的api的操作用户, None 默认是用root用户
    get_riak_payload_func: str = None  # 上下文中MysqlActPayload类的获取参数方法名称。空则传入None
    cluster_type: str = None  # 表示操作的集群类型,如果过程中不需要这个变量，则可以传None
    cluster: dict = field(default_factory=dict)  # 表示单据执行的集群信息，比如集群名称，集群域名等


@dataclass()
class ExecActuatorKwargs(ExecActuatorBaseKwargs):
    """
    针对手输IP的场景
    """

    exec_ip: Optional[Any] = None  # 表示执行的ip，多个ip传入list类型，当个ip传入str类型，空则传入None，针对手输ip场景


@dataclass()
class DownloadMediaBaseKwargs:
    """
    定义在介质中心下发介质的私用变量结构体
    """

    bk_cloud_id: int  # 对应的云区域ID
    file_list: list  # 需要传送的源文件列表
    file_type: Optional[MediumFileTypeEnum] = MediumFileTypeEnum.Repo.value
    file_target_path: str = None  # 表示下载到目标机器的路径，如果传None,默认则传/data/install


@dataclass()
class DownloadMediaKwargs(DownloadMediaBaseKwargs):
    """
    针对手输IP的场景
    """

    exec_ip: Optional[Any] = None  # 表示执行的ip，多个ip传入list类型，当个ip传入str类型，空则传入None，针对手输ip场景


@dataclass()
class DownloadMediaKwargsFromTrans(DownloadMediaBaseKwargs):
    """
    针对资源池获取IP的场景
    """

    get_trans_data_ip_var: str = None  # 表示在上下文获取ip信息的变量名称。空则传入None


@dataclass()
class DBMetaFuncKwargs:
    """
    修改元数据的函数
    """

    db_meta_class_func: str = None
    cluster: dict = field(default_factory=dict)  # 表示单据执行的集群信息，比如集群名称，集群域名等
    is_update_trans_data: bool = False  # 表示是否把流程中上下文trans_data合并到cluster信息，默认不合并
