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
from typing import Any, Dict, Optional

from backend.flow.consts import CloudDBHATypeEnum


@dataclass()
class CloudServiceActKwargs:
    """
    定义云区域服务活动节点的私有变量dataclass类
    """

    bk_cloud_id: int = None  # 全局的云区域ID
    exec_ip: Optional[Any] = None  # 表示执行的IP+云区域
    get_payload_func: str = None  # 上下文中CloudActPayload类的获取参数方法名称。空则传入None
    file_list: list = field(default_factory=list)  # 传入文件传输节点的文件名称列表，默认空字典
    script_tpl: str = None  # 部署脚本模板
    ticket_data: dict = None  # 单据部署参数


@dataclass()
class CloudPrivilegeFlushActKwargs:
    """
    定义权限刷新节点的私有变量dataclass类
    """

    access_hosts: list = None  # super account所准许的机器列表
    user: str = ""  # 加密后的用户
    pwd: str = ""  # 加密后的密码
    type: str = ""  # 权限增加/删除


@dataclass()
class CloudDNSFlushActKwargs:
    """
    定义dns nameserver刷新节点的私有变量dataclass类
    """

    dns_ips: list = field(default_factory=list)  # 传入的dns的ip列表
    flush_type: str = ""  # 刷新的类型


@dataclass()
class CloudProxyKwargs:
    """
    定义云区域元数据写入私有变量dataclass类
    """

    bk_cloud_id: int = None  # 全局的云区域ID
    host_infos: Optional[Any] = None  # 服务的主机信息
    proxy_func_name: str = None  # 写入数据的名称
    details: Dict[str, Any] = None  # 额外的details信息


@dataclass()
class CloudConfKwargs(CloudServiceActKwargs):
    """
    部署带有配置文件服务的私有变量dataclass类
    """

    conf_file_name: str = None  # 部署配置文件名


@dataclass()
class CloudDBHAKwargs:
    """
    dbha服务部署所需要的私有变量dataclass类
    """

    dbha_type: CloudDBHATypeEnum = None  # dbha部署的类型：gm/agent
    nginx_internal_domain: str = None  # nginx内网地址
    name_service_domain: str = None  # 名字服务的内网地址

    user: str = ""  # 超级账户的用户名
    pwd: str = ""  # 超级账户的密码
    plain_user: str = ""  # 超级账户的用户名-明文
    plain_pwd: str = ""  # 超级账户的密码-明文


@dataclass()
class CloudDNSKwargs:
    """
    dns服务部署所需要的私有变量dataclass类
    """

    nginx_internal_domain: str = None  # nginx内网地址


@dataclass()
class CloudDRSKwargs:
    """
    drs服务部署所需要的私有变量dataclass类
    """

    user: str = ""  # 超级账户的用户名
    pwd: str = ""  # 超级账户的密码
    plain_user: str = ""  # 超级账户的用户名-明文
    plain_pwd: str = ""  # 超级账户的密码-明文


@dataclass()
class CloudServiceDetail:
    """
    云区域服务写入DBExtension的detail数据类
    """

    bk_cloud_id: int = None  # 云区域ID
    ip: str = None  # 服务部署的主机IP
    bk_host_id: int = None  # 服务部署的主机ID


@dataclass()
class CloudNginxDetail(CloudServiceDetail):
    """
    Nginx服务的detail数据
    """

    dbm_port: int = 80  # dbm端口
    manage_port: int = 8080  # 管理端服务端口
    bk_outer_ip: str = None  # nginx外网地址


@dataclass()
class CloudDRSDetail(CloudServiceDetail):
    """
    DRS服务的detail数据类
    """

    drs_port: str = ""  # 部署drs服务的机器port
    user: str = ""  # 加密后的用户
    pwd: str = ""  # 加密后的密码


@dataclass()
class CloudDNSDetail(CloudServiceDetail):
    """
    DNS服务的detail数据类
    """

    pass


@dataclass()
class CloudDBHADetail(CloudServiceDetail):
    """
    DBHA服务的detail数据类
    """

    user: str = ""  # 加密后的用户
    pwd: str = ""  # 加密后的密码
    bk_city_code: int = None  # 部署机器的城市代码
    bk_city_name: str = ""  # 部署机器的城市信息
    dbha_type: str = ""  # gm/agent


@dataclass()
class CloudRedisDTSDetail(CloudServiceDetail):
    """
    Redis DTS服务的detail数据类
    """

    bk_city_name: str = ""  # 部署机器的城市信息

    pass
