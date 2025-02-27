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

from backend.flow.utils.base.validate_handler import ValidateHandler


@dataclass()
class Instance:
    """
    定义实例通用结构体
    @attributes host 机器ip，ipv4格式
    @attributes bk_cloud_id 机器所在云区域, 默认值为0
    @attributes port 实例port
    """

    __dataclass_fields__ = None

    host: str
    port: int
    bk_cloud_id: int = 0

    def __init__(self, **kwargs):
        for _field in Instance.__dataclass_fields__:
            setattr(self, _field, kwargs.get(_field))


def validate_list(value) -> None:
    """
    判断传入的类型变量是否是list
    """
    if not isinstance(value, list):
        raise ValueError(f"{value} variable is not a list")


@dataclass()
class AddUnLockTicketTypeKwargs(ValidateHandler):
    """
    定义解除单据互斥锁定义
    @attributes cluster_ids: 本次参与解锁的集群ID列表，默认空，填入案例：[1,2,3....]
    @attributes unlock_ticket_type_list: 本次解锁的单据类型范围，默认空，
    填入案例：[TicketType.MYSQL_SINGLE_APPLY, TicketType.MYSQL_ADD_SLAVE....]
    也可以全解锁，案例：['*']
    只有列表中有‘*’ 元素存在，代表全解锁
    """

    cluster_ids: list = field(default_factory=list, metadata={"validate": validate_list})
    unlock_ticket_type_list: list = field(default_factory=list, metadata={"validate": validate_list})


@dataclass()
class ReleaseUnLockTicketTypeKwargs(ValidateHandler):
    """
    定义释放解除单据互斥锁定义
    @attributes cluster_ids: 本次参与解锁的集群ID列表，默认空，填入案例：[1,2,3....]
    @attributes release_unlock_ticket_type_list: 本次解锁的单据类型范围，默认空，
    填入案例：[TicketType.MYSQL_SINGLE_APPLY, TicketType.MYSQL_ADD_SLAVE....]
    """

    cluster_ids: list = field(default_factory=list, metadata={"validate": validate_list})
    release_unlock_ticket_type_list: list = field(default_factory=list, metadata={"validate": validate_list})
