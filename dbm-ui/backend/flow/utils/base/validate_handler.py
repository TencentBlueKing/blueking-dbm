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


@dataclass
class ValidateHandler:
    def __init__(self):
        self.__dataclass_fields__ = None

    def __post_init__(self):
        for key, value in self.__dataclass_fields__.items():
            validate_func = value.metadata.get("validate")
            if validate_func:
                try:
                    validate_func(getattr(self, key))
                except Exception as err:
                    raise ValueError(f"[{key}]:{err}")


def validate_list(value) -> None:
    """
    判断传入的类型变量是否是list
    """
    if not isinstance(value, list):
        raise ValueError(f"{value} variable is not a list")


def validate_dict(value) -> None:
    """
    判断传入的类型变量是否是dict
    """
    if not isinstance(value, dict):
        raise ValueError(f"{value} variable is not a dict")


def validate_int(value) -> None:
    """
    判断传入的类型变量是否是int类型
    """
    if not isinstance(value, int):
        raise ValueError(f"{value} variable is not a int")


def validate_string(value) -> None:
    """
    判断传入的类型变量是否是str类型
    """
    if not isinstance(value, str):
        raise ValueError(f"{value} variable is not a string")


def validate_ip(value) -> None:
    """
    判断传入的类型变量是否是合法ip
    """
    if not isinstance(value, str):
        raise ValueError(f"{value} is not a valid ipv4 \n")
    try:
        ipaddress.IPv4Address(value)
        return None
    except ipaddress.AddressValueError:
        raise ValueError(f"{value} is not a valid ipv4 \n")


def validate_port(value) -> None:
    """
    判断传入的类型变量是否是合法端口
    """
    if not isinstance(value, int) or value <= 0 or value > 65535:
        raise ValueError(f"{value} is not a valid port \n")


def validate_str_in_list(value, is_allow_null: bool = False) -> None:
    """
    判断传入的类型变量是否是List[str]类型
    """
    if not isinstance(value, list):
        raise ValueError(f"{value} variable is not a list")

    if not value and not is_allow_null:
        raise ValueError(f"{value} variable is empty, check")

    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{item} is not a valid str in {value} \n")


def validate_int_in_list(value, is_allow_null: bool = False) -> None:
    """
    判断传入的类型变量是否是List[int]类型
    """
    if not isinstance(value, list):
        raise ValueError(f"{value} variable is not a list")

    if not value and not is_allow_null:
        raise ValueError(f"{value} variable is empty, check")

    for item in value:
        if not isinstance(item, int):
            raise ValueError(f"{item} is not a valid int in {value} \n")


def validate_ip_in_list(value, is_allow_null: bool = False) -> None:
    """
    判断传入的类型变量是否是List[ip]类型
    """
    if not isinstance(value, list):
        raise ValueError(f"{value} variable is not a list")

    if not value and not is_allow_null:
        raise ValueError("variable is empty, check")

    for item in value:
        try:
            validate_ip(item)
        except Exception as err:
            raise ValueError(err)


def validate_port_in_list(value, is_allow_null: bool = False) -> None:
    """
    判断传入的类型变量是否是List[port]类型
    """
    if not isinstance(value, list):
        raise ValueError(f"{value} variable is not a list")

    if not value and not is_allow_null:
        raise ValueError(f"{value} variable is empty, check")

    for item in value:
        try:
            validate_port(item)
        except Exception as err:
            raise ValueError(err)
