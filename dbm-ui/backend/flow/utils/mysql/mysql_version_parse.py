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
import logging
import re

from backend.components.db_remote_service.client import DRSApi
from backend.constants import IP_PORT_DIVIDER

logger = logging.getLogger("flow")


def get_sub_version_by_pkg_name(pkg_name: str) -> str:
    re_pattern = r"([\d]+).?([\d]+)?.?([\d]+)?"
    result = re.findall(re_pattern, pkg_name)
    if len(result) == 0:
        return ""
    billion, thousand, single = result[0]
    return "{}.{}.{}".format(billion, thousand, single)


def mysql_version_parse(mysql_version: str) -> int:
    re_pattern = r"([\d]+).?([\d]+)?.?([\d]+)?"
    result = re.findall(re_pattern, mysql_version)

    if len(result) == 0:
        return 0

    billion, thousand, single = result[0]

    total = 0

    if billion != "":
        total += int(billion) * 1000000

    if thousand != "":
        total += int(thousand) * 1000

    if single != "":
        total += int(single)

    return total


def major_version_parse(mysql_version: str):
    re_pattern = r"([\d]+).?([\d]+)?.?([\d]+)?"
    result = re.findall(re_pattern, mysql_version)

    if len(result) == 0:
        return 0

    billion, thousand, single = result[0]

    major_version = 0

    if billion != "":
        major_version += int(billion) * 1000000

    if thousand != "":
        major_version += int(thousand) * 1000

    return major_version, single


# 解析tmysql 版本号码
# mysql-5.6.24-linux-x86_64-tmysql-2.1.5-gcs
# 解析 tmysql-2.1.5 成数字 2.1.5  => 2 * 1000000 + 1 * 1000 + 5
def tmysql_version_parse(mysql_version: str) -> int:
    re_pattern = r"tmysql-([\d]+).?([\d]+)?.?([\d]+)?"
    result = re.findall(re_pattern, mysql_version)

    if len(result) == 0:
        return 0

    billion, thousand, single = result[0]

    total = 0

    if billion != "":
        total += int(billion) * 1000000

    if thousand != "":
        total += int(thousand) * 1000

    if single != "":
        total += int(single)

    return total


def proxy_version_parse(proxy_version: str) -> int:
    re_pattern = r"([\d]+).?([\d]+)?.?([\d]+)?"
    result = re.findall(re_pattern, proxy_version)

    if len(result) == 0:
        return 0

    billion, thousand, single = result[0]

    total = 0

    if billion != "":
        total += int(billion) * 1000000

    if thousand != "":
        total += int(thousand) * 1000

    if single != "":
        total += int(single)

    return total


def get_online_proxy_version(ip: str, port: int, bk_cloud_id: int):
    """
    在线获取proxy的版本
    """
    logger.info(f"param: {ip}:{port}")
    body = {
        "addresses": ["{}{}{}".format(ip, IP_PORT_DIVIDER, port)],
        "cmds": ["select version"],
        "force": False,
        "bk_cloud_id": bk_cloud_id,
    }

    resp = DRSApi.proxyrpc(body)
    logger.info(f"query version resp: {resp}")

    if not resp or len(resp) == 0:
        return ""

    result = resp[0].get("version")
    if len(result.split(" ")) >= 2:
        return result.split(" ")[1]
    return ""


def get_online_mysql_version(ip: str, port: int, bk_cloud_id: int):
    """
    在线获取mysql的版本
    """
    logger.info(f"param: {ip}:{port}")
    body = {
        "addresses": ["{}{}{}".format(ip, IP_PORT_DIVIDER, port)],
        "cmds": ["select @@version as version"],
        "force": False,
        "bk_cloud_id": bk_cloud_id,
    }

    resp = DRSApi.rpc(body)
    logger.info(f"query version resp: {resp[0]}")

    if not resp or len(resp) == 0:
        return ""

    return resp[0]["cmd_results"][0]["table_data"][0].get("version")
