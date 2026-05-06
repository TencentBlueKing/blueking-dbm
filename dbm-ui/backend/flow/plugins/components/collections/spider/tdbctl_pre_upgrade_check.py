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
import time

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.spider.tdbctl_check_utils import check_tdbctl_primary_and_nodes_status

logger = logging.getLogger("flow")


class TdbctlPreUpgradeCheckService(BaseService):
    """
    在 tdbctl 主节点上执行升级前/升级后检查

    检查项：
    1. TDBCTL GET PRIMARY 获取主节点成功，且为当前节点
    2. 执行 select * from information_schema.tdbctl_nodes; 检查：
       - 每个节点的 STATUS 均为 Online
       - 每个从 TDBCTL 节点的角色为 Secondary
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        self.log_info(_("传入参数:{}").format(kwargs))

        ip = kwargs["ip"]
        port = kwargs["port"]
        bk_cloud_id = kwargs["bk_cloud_id"]
        check_type = kwargs.get("check_type", "pre_upgrade")  # pre_upgrade 或 post_upgrade

        if check_type == "pre_upgrade":
            self.log_info(_("开始执行升级前检查"))
        else:
            self.log_info(_("开始执行升级后检查"))

        # 调用公共检查函数，带重试逻辑
        # 重试配置：最多重试15次，使用递增的时间间隔
        max_retries = 15
        retry_intervals = [10, 10, 10, 10, 10, 10, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]  # 秒
        success = False
        error_msg = ""

        for attempt in range(max_retries):
            success, error_msg = check_tdbctl_primary_and_nodes_status(ip, port, bk_cloud_id)
            if success:
                break
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                retry_interval = retry_intervals[attempt]
                self.log_info(_("第 {} 次检查失败，等待 {} 秒后重试").format(attempt + 1, retry_interval))
                time.sleep(retry_interval)
            else:
                self.log_error(_("第 {} 次检查失败，已达到最大重试次数").format(attempt + 1))

        if success:
            if check_type == "pre_upgrade":
                self.log_info(_("升级前检查全部通过"))
            else:
                self.log_info(_("升级后检查全部通过"))
            return True
        else:
            self.log_error(error_msg)
            return False


class TdbctlPreUpgradeCheckComponent(Component):
    name = __name__
    code = "tdbctl_pre_upgrade_check"
    bound_service = TdbctlPreUpgradeCheckService
