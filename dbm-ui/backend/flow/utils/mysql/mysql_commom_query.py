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

from django.utils.translation import gettext as _

from backend.components.db_remote_service.client import DRSApi
from backend.constants import IP_PORT_DIVIDER

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
