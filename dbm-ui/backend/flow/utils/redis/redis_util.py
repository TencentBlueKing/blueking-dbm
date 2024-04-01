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
import re
from typing import Dict, List

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum


def domain_without_port(domain):
    end_port_reg = re.compile(r"(\:\d+$)|(#\d+$)")
    if end_port_reg.search(domain):
        return end_port_reg.sub("", domain)
    return domain


def check_domain(domain):
    match = re.search(r"^[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62}){2,8}\.*(#(\d+))?$", domain)
    if match:
        return True
    return False


def convert_version_to_uint(version):
    version = version.strip()
    if not version:
        return 0, None
    list01 = version.split(".")
    billion = ""
    thousand = ""
    single = ""
    if len(list01) == 0:
        err = ValueError(f"version:{version} format not correct")
        return 0, err
    billion = list01[0]
    thousand = list01[1] if len(list01) >= 2 else ""
    single = list01[2] if len(list01) >= 3 else ""
    total = 0
    if billion:
        try:
            b = int(billion)
            total += b * 1000000
        except ValueError as e:
            err = ValueError(f"convertVersionToUint int() fail, err:{e}, billion:{billion}, version:{version}")
            return 0, err
    if thousand:
        try:
            t = int(thousand)
            total += t * 1000
        except ValueError as e:
            err = ValueError(f"convertVersionToUint int() fail, err:{e}, thousand:{thousand}, version:{version}")
            return 0, err
    if single:
        try:
            s = int(single)
            total += s
        except ValueError as e:
            err = ValueError(f"convertVersionToUint int() fail, err:{e}, single:{single}, version:{version}")
            return 0, err
    return total, None


# redis-6.2.7.tar.gz => (6002007, 0, None)
# redis-2.8.17-rocksdb-v1.3.10.tar.gz => (2008017, 1003010, None)
def version_parse(version):
    reg01 = re.compile(r"[\d+.]+")
    rets = reg01.findall(version)
    if len(rets) == 0:
        err = ValueError(f"TendisVersionParse version:{version} format not correct")
        return 0, 0, err
    base_version = 0
    sub_version = 0
    if len(rets) >= 1:
        base_version, err = convert_version_to_uint(rets[0])
        if err:
            return 0, 0, err
    if len(rets) >= 2:
        sub_version, err = convert_version_to_uint(rets[1])
        if err:
            return 0, 0, err
    return base_version, sub_version, None


# 判断两个版本是否相等
def version_equal(version1, version2):
    base_version1, sub_version1, err = version_parse(version1)
    if err:
        return False, err
    base_version2, sub_version2, err = version_parse(version2)
    if err:
        return False, err
    return base_version1 == base_version2 and sub_version1 == sub_version2, None


# 根据db_version 获取 redis 最新 Package
def get_latest_redis_package_by_version(db_version):
    pkg_type = MediumEnum.Redis
    if db_version.startswith("TendisSSD"):
        pkg_type = MediumEnum.TendisSsd
    if db_version.startswith("Tendisplus"):
        pkg_type = MediumEnum.TendisPlus
    redis_pkg = Package.get_latest_package(version=db_version, pkg_type=pkg_type, db_type=DBType.Redis)
    return redis_pkg


def humanbytes(B):
    """
    将字节数转换为更易读的的字符串
    如: 11111111111 -> 10.35 GB
    如: 891743743 -> 850.43 MB
    """
    # 定义不同单位的字节数
    KB = float(1024)
    MB = float(KB**2)
    GB = float(KB**3)
    TB = float(KB**4)
    PB = float(KB**5)

    # 根据字节数选择合适的单位
    if B < KB:
        return f"{B:.0f} {'Bytes' if B == 1 else 'Byte'}"
    elif KB <= B < MB:
        return f"{B / KB:.2f} KB"
    elif MB <= B < GB:
        return f"{B / MB:.2f} MB"
    elif GB <= B < TB:
        return f"{B / GB:.2f} GB"
    elif TB <= B < PB:
        return f"{B / TB:.2f} TB"
    elif B >= PB:
        return f"{B / PB:.2f} PB"


UNITS = {None: 1, "B": 1, "KB": 2**10, "MB": 2**20, "GB": 2**30, "TB": 2**40, "PB": 2**50}


def parse_human_size(size):
    """
    解析人类可读的字符串为字节数
    如: 100GB -> 107374182400
    如: 11.1 MB -> 11639193
    """
    if isinstance(size, int):
        return size
    m = re.match(r"^(\d+(?:\.\d+)?)\s*([KMGTP]?B)?$", size.upper())
    if m:
        number, unit = m.groups()
        return int(float(number) * UNITS[unit])
    raise ValueError("Invalid human size")


def decode_info_cmd(info_str: str) -> Dict:
    """
    将info命令返回的 used_memory:12241256\r\nused_memory_human:11.67M
    接些成字典:{
        "used_memory":"12241256",
        "used_memory_human":"11.67M"
    }
    """
    info_ret: Dict[str, dict] = {}
    info_list: List = info_str.split("\n")
    for info_item in info_list:
        info_item = info_item.strip()
        if info_item.startswith("#"):
            continue
        if len(info_item) == 0:
            continue
        tmp_list = info_item.split(IP_PORT_DIVIDER, 1)
        if len(tmp_list) < 2:
            continue
        tmp_list[0] = tmp_list[0].strip()
        tmp_list[1] = tmp_list[1].strip()
        info_ret[tmp_list[0]] = tmp_list[1]
    return info_ret
