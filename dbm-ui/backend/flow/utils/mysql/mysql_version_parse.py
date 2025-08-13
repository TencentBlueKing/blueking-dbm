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

from django.utils.translation import ugettext as _

from backend.components.db_remote_service.client import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_services.mysql.remote_service.exceptions import RemoteServiceBaseException

logger = logging.getLogger("flow")


def get_sub_version_by_pkg_name(pkg_name: str) -> str:
    re_pattern = r"([\d]+).?([\d]+)?.?([\d]+)?"
    result = re.findall(re_pattern, pkg_name)
    if len(result) == 0:
        return ""
    billion, thousand, single = result[0]
    return "{}.{}.{}".format(billion, thousand, single)


def get_spider_sub_version_by_pkg_name(pkg_name: str) -> str:
    re_pattern = r"tspider-([\d]+).?([\d]+)?.?([\d]+)?"
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


def spider_major_version_parse(mysql_version: str, has_prefix: bool = False):
    """
    解析spider版本字符串，返回主版本号和子版本号（均为数字，便于比较）

    :param mysql_version: 版本字符串，如 "tspider-3.6.20" 或 "3.6.20"
    :param has_prefix: 是否带有前缀（如"tspider-"），默认为False
    :return: (major_version, sub_version)
        - major_version: 主版本号（如3.6.20中的3，返回3000000）
        - sub_version: 子版本号（如3.6.20中的6.20，返回6020）
        - 若解析失败，返回(0, 0)
    """
    # 根据是否有前缀选择正则表达式
    re_pattern = r"tspider-([\d]+)\.?([\d]+)?\.?([\d]+)?" if has_prefix else r"([\d]+)\.?([\d]+)?\.?([\d]+)?"
    result = re.findall(re_pattern, mysql_version)

    if not result:
        # 解析失败，返回(0, 0)
        return 0, 0

    billion, thousand, single = result[0]

    # 主版本号：只取第一个数字（如3），乘以1000000
    major_version = int(billion) * 1000000 if billion else 0

    # 子版本号：第二个数字乘以1000，加上第三个数字
    sub_version = 0
    if thousand:
        sub_version += int(thousand) * 1000
    if single:
        sub_version += int(single)

    return major_version, sub_version


def major_version_parse(mysql_version: str):
    re_pattern = r"([\d]+).?([\d]+)?.?([\d]+)?"
    result = re.findall(re_pattern, mysql_version)

    if len(result) == 0:
        return 0, 0

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


def tspider_version_parse(mysql_version: str) -> int:
    re_pattern = r"tspider-([\d]+).?([\d]+)?.?([\d]+)?"
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

    if resp[0]["error_msg"]:
        raise RemoteServiceBaseException(_("DRS调用失败，错误信息: {}").format(resp[0]["error_msg"]))

    if not resp or len(resp) == 0:
        return ""

    return resp[0]["cmd_results"][0]["table_data"][0].get("version")
