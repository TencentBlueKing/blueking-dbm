"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import ipaddress
from dataclasses import dataclass
from typing import List

from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.flow.utils.sqlserver.sqlserver_db_meta import SqlserverDBMeta
from backend.flow.utils.sqlserver.sqlserver_host import Host


@dataclass
class SqlserverInstance:
    """
    sqlserver实例信息基类
    @attributes ip 实例ip，ipv4格式
    @attributes port 实例端口
    @attributes bk_cloud_id 机器所在云区域
    @attributes is_new 是否是这次加入的
    """

    __dataclass_fields__ = None
    host: str
    port: int
    bk_cloud_id: int
    is_new: bool

    def __init__(self, **kwargs):
        for field in SqlserverInstance.__dataclass_fields__:
            setattr(self, field, kwargs.get(field))


@dataclass
class SqlserverCluster:
    """
    sqlserver实例信息基类
    @attributes ip 机器ip，ipv4格式
    @attributes bk_cloud_id 机器所在云区域
    """

    __dataclass_fields__ = None
    port: int
    immutable_domain: str

    def __init__(self, **kwargs):
        for field in SqlserverCluster.__dataclass_fields__:
            setattr(self, field, kwargs.get(field))


@dataclass
class ValidateHandler:
    def __init__(self):
        self.__dataclass_fields__ = None

    def __post_init__(self):
        for key, value in self.__dataclass_fields__.items():
            validate_func = value.metadata.get("validate")
            if validate_func:
                validate_func(getattr(self, key))


def validate_get_payload_func(value: str) -> None:
    """
    判断get_payload_func变量
    """
    if not hasattr(SqlserverActPayload, value):
        raise ValueError(f"There is no {value} method in the SqlserverActPayload class")


def validate_get_dbmeta_func(value: str) -> None:
    """
    判断get_dbmeta_func变量
    """
    if not hasattr(SqlserverDBMeta, value):
        raise ValueError(f"There is no {value} method in the SqlserverDBMeta class")


def validate_hosts(value: List[Host]) -> None:
    """
    判断传入的hosts类型变量
    """
    if not isinstance(value, list):
        raise ValueError("ips variable is not a list")
    for item in value:
        if not isinstance(item, Host):
            raise ValueError(f"/{item}/ One of the elements in the list is in the wrong format")
        if not ipaddress.ip_address(item.ip):
            raise ValueError(f"/{item.ip}/ is not ipv4")
        if not isinstance(item.bk_cloud_id, int) or item.bk_cloud_id < 0:
            raise ValueError(f"/{item.bk_cloud_id}/ is illegal-value")


def validate_instances(value: List[SqlserverInstance]) -> None:
    """
    判断传入的SqlserverInstance类型变量
    """
    if not isinstance(value, list):
        raise ValueError("ips variable is not a list")
    for item in value:
        if not isinstance(item, SqlserverInstance):
            raise ValueError(f"/{item}/ One of the elements in the list is in the wrong format")
        if not ipaddress.ip_address(item.ip):
            raise ValueError(f"/{item.ip}/ is not ipv4")
        if not isinstance(item.port, int) or item.port <= 0 or item.port >= 65535:
            raise ValueError(f"/{item.port}/ is is illegal-port-value")
        if not isinstance(item.bk_cloud_id, int) or item.bk_cloud_id < 0:
            raise ValueError(f"/{item.bk_cloud_id}/ is illegal-bk-cloud_id-value")
