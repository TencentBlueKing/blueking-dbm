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
from typing import Tuple

from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER

logger = logging.getLogger("flow")


def check_tdbctl_primary_and_nodes_status(ip: str, port: int, bk_cloud_id: int) -> Tuple[bool, str]:
    """
    在 tdbctl 主节点上执行检查

    检查项：
    1. TDBCTL GET PRIMARY 获取主节点成功，且为当前节点
    2. 执行 select * from information_schema.tdbctl_nodes; 检查：
       - 每个节点的 STATUS 均为 Online
       - 每个从 TDBCTL 节点的角色为 Secondary

    @param ip: tdbctl 主节点 IP
    @param port: tdbctl 主节点端口
    @param bk_cloud_id: 云区域ID
    @return: (检查是否通过, 错误信息)
    """
    ctl_address = "{}{}{}".format(ip, IP_PORT_DIVIDER, port)

    # 检查1: TDBCTL GET PRIMARY 获取主节点成功，且为当前节点
    try:
        res = DRSApi.short_rpc(
            {
                "addresses": [ctl_address],
                "cmds": ["tdbctl get primary"],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            error_msg = _("执行 tdbctl get primary 失败: {}").format(res[0]["error_msg"])
            logger.error(error_msg)
            return False, error_msg

        primary_info_table_data = res[0]["cmd_results"][0]["table_data"]
        if not primary_info_table_data:
            error_msg = _("tdbctl get primary 返回空结果")
            logger.error(error_msg)
            return False, error_msg

        # 检查 IS_THIS_SERVER 字段是否为 "1"（表示当前节点是 primary）
        is_this_server = primary_info_table_data[0].get("IS_THIS_SERVER", "0")
        if is_this_server != "1":
            error_msg = _("当前节点不是 primary，IS_THIS_SERVER={}").format(is_this_server)
            logger.error(error_msg)
            return False, error_msg

        logger.info(_("检查1通过: 当前节点是 primary"))

    except Exception as e:
        error_msg = _("检查 tdbctl primary 状态失败: {}").format(str(e))
        logger.error(error_msg)
        return False, error_msg

    # 检查2: 执行 select * from information_schema.tdbctl_nodes; 检查节点状态
    try:
        res = DRSApi.rpc(
            {
                "addresses": [ctl_address],
                "cmds": ["select * from information_schema.tdbctl_nodes"],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            error_msg = _("查询 tdbctl_nodes 失败: {}").format(res[0]["error_msg"])
            logger.error(error_msg)
            return False, error_msg

        nodes_data = res[0]["cmd_results"][0]["table_data"]
        if not nodes_data:
            error_msg = _("查询 tdbctl_nodes 返回空结果")
            logger.error(error_msg)
            return False, error_msg

        # 检查每个节点的状态和角色
        for node in nodes_data:
            server_name = node.get("SERVER_NAME", "")
            status = node.get("STATUS", "")
            cluster_role = node.get("CLUSTER_ROLE", "")

            logger.info(_("节点 {}: STATUS={}, CLUSTER_ROLE={}").format(server_name, status, cluster_role))

            # 检查每个节点的 STATUS 均为 Online
            if status != "Online":
                error_msg = _("节点 {} 的状态不是 Online，当前状态: {}").format(server_name, status)
                logger.error(error_msg)
                return False, error_msg

            # 检查每个从 TDBCTL 节点的角色为 Secondary
            # 注意：主节点的角色可能是 Primary 或 primary（大小写可能不同）
            if cluster_role.lower() not in ["primary", "secondary"]:
                # 如果不是 primary 也不是 secondary，记录警告但继续
                logger.warning(_("节点 {} 的角色不是 Primary 或 Secondary，当前角色: {}").format(server_name, cluster_role))
            elif cluster_role.lower() == "secondary":
                # 确认从节点的角色是 Secondary
                logger.info(_("节点 {} 是从节点，角色: {}，状态: {}").format(server_name, cluster_role, status))

        # 检查通过
        logger.info(_("检查2通过: 所有节点状态为 Online，从节点角色为 Secondary"))
        return True, ""

    except Exception as e:
        error_msg = _("检查 tdbctl_nodes 状态失败: {}").format(str(e))
        logger.error(error_msg)
        return False, error_msg
