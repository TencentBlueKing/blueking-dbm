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
import logging.config
from typing import List

from django.utils.translation import gettext as _

from backend.components.db_remote_service.client import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import StorageInstance
from backend.flow.utils.mysql.mysql_version_parse import mysql_version_parse

logger = logging.getLogger("flow")


def query_mysql_variables(host: str, port: int, bk_cloud_id: int):
    """
    查询远程节点变量
    """
    body = {
        "addresses": ["{}{}{}".format(host, IP_PORT_DIVIDER, port)],
        "cmds": ["show global variables;"],
        "force": False,
        "bk_cloud_id": bk_cloud_id,
    }
    resp = DRSApi.rpc(body)
    logger.info(f"query vaiables {resp}")
    if not resp and len(resp) < 1:
        raise Exception(_("DRS{}:{}查询变量失败,返回为空值").format(host, port))

    if not resp[0]["cmd_results"]:
        raise Exception(_("DRS查询字符集失败：{}").format(resp[0]["error_msg"]))

    var_list = resp[0]["cmd_results"][0]["table_data"]

    var_map = {}
    for var_item in var_list:
        var_name = var_item["Variable_name"]
        val = var_item["Value"]
        var_map[var_name] = val
    return var_map


def show_user_host_for_host(host: str, instance: StorageInstance):
    """
    根据host查询账号信息
    """
    res = DRSApi.rpc(
        {
            "addresses": [instance.ip_port],
            "cmds": [f"select concat('`',user,'`@`',host,'`') as user_host from mysql.user where host = '{host}'"],
            "force": False,
            "bk_cloud_id": instance.machine.bk_cloud_id,
        }
    )
    if res[0]["error_msg"]:
        logger.error(f"[{instance.ip_port}] get user info [{host}] failed: [{res['error_msg']}]")
        return False, []

    return True, [list(item.values())[0] for item in res[0]["cmd_results"][0]["table_data"]]


def show_privilege_for_user(db_version: str, host: str, instance: StorageInstance):
    """
    根据user_host 在实例查询授权情况，并拼接成对应的版本的授权语句
    """
    result, user_hosts = show_user_host_for_host(host=host, instance=instance)
    if not result:
        # 这里是异常退出
        return result, []
    if not user_hosts:
        # 这里查询为空则正常退出
        return True, []

    grants_sql = []
    if mysql_version_parse(db_version) >= mysql_version_parse("5.7"):
        res = DRSApi.rpc(
            {
                "addresses": [instance.ip_port],
                "cmds": [f"show create user {u} " for u in user_hosts],
                "force": False,
                "bk_cloud_id": instance.machine.bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            logger.error(f"[{instance.ip_port}] show create user failed: [{res[0]['error_msg']}]")
            return False, []
        grants_sql.extend([list(i.values())[0] for item in res[0]["cmd_results"] for i in item["table_data"]])

    res = DRSApi.rpc(
        {
            "addresses": [instance.ip_port],
            "cmds": [f"show grants for {u} " for u in user_hosts],
            "force": False,
            "bk_cloud_id": instance.machine.bk_cloud_id,
        }
    )
    if res[0]["error_msg"]:
        logger.error(f"[{instance.ip_port}] show grants failed: [{res[0]['error_msg']}]")
        return False, []

    grants_sql.extend([list(i.values())[0] for item in res[0]["cmd_results"] for i in item["table_data"]])
    return True, grants_sql


def check_backend_in_proxy(proxys: List[str], bk_cloud_id: int):
    """
    检测传入的proxy是否1.1.1.1:3306
    """
    res = DRSApi.proxyrpc(
        {
            "addresses": proxys,
            "cmds": ["SELECT * FROM backends;"],
            "force": False,
            "bk_cloud_id": bk_cloud_id,
        }
    )
    for i in res:
        if i["error_msg"]:
            logger.error(f"get proxy backends failed: [{i['error_msg']}]")
            return False

    is_pass = True
    for i in res[0]["cmd_results"]:
        backend_address = str(i["table_data"][0]["address"]).strip()
        if backend_address != "1.1.1.1:3306":
            logger.error(f"[{res[0]['address']}] the backends is not empty [{backend_address}] ")
            is_pass = False

    return is_pass
