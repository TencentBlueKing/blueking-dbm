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

from backend.configuration.constants import DBType
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
