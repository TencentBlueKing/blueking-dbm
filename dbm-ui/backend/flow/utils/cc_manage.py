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

from django.utils.translation import ugettext_lazy as _

from backend import env
from backend.components import CCApi
from backend.configuration.constants import FREE_BK_MODULE_ID
from backend.configuration.models import SystemSettings
from backend.db_meta.models import Machine
from backend.db_services.ipchooser.constants import IDLE_HOST_MODULE

logger = logging.getLogger("flow")


class CcManage(object):
    @classmethod
    def transfer_machines(cls, bk_biz_id: int, bk_cloud_id: int, ip_modules: list):

        free_bk_module_id = 0
        transfer_groups = []
        bk_host_ids = []
        for transfer_group in ip_modules:
            ips = transfer_group["ips"]
            kwargs = {
                "fields": [
                    "bk_host_id",
                    "bk_host_innerip",
                ],
                "host_property_filter": {
                    "condition": "AND",
                    "rules": [
                        {"field": "bk_host_innerip", "operator": "in", "value": ips},
                        {"field": "bk_cloud_id", "operator": "equal", "value": bk_cloud_id},
                    ],
                },
            }
            res = CCApi.list_hosts_without_biz(kwargs)

            group_bk_host_ids = []
            for host_info in res["info"]:
                group_bk_host_ids.append(host_info["bk_host_id"])
                bk_host_ids.append(host_info["bk_host_id"])

            if len(group_bk_host_ids) != len(ips):
                raise ValueError(_("查询主机bk_host_id失败[数量不匹配]"), kwargs, res)

            transfer_groups.append({"bk_module_id": transfer_group["bk_module_id"], "bk_host_id": group_bk_host_ids})

        if env.DBA_APP_BK_BIZ_ID != bk_biz_id:
            # 获取dba空闲机模块的bk_module_id
            internal_set_info = CCApi.get_biz_internal_module({"bk_biz_id": env.DBA_APP_BK_BIZ_ID}, use_admin=True)
            for module in internal_set_info["module"]:
                if module["default"] == IDLE_HOST_MODULE:
                    free_bk_module_id = module["bk_module_id"]

            if free_bk_module_id == 0:
                raise ValueError(_("查询空闲机模块ID bk_module_id 失败"), env.DBA_APP_BK_BIZ_ID)

            # 从业务挪到dba空闲机模块下
            CCApi.transfer_host_across_biz(
                {
                    "src_bk_biz_id": bk_biz_id,
                    "dst_bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                    "bk_host_id": bk_host_ids,
                    "bk_module_id": free_bk_module_id,
                    "is_increment": False,
                },
                use_admin=True,
            )

        # 按模块转移：db业务空闲机 -> db业务下的集群模块
        for transfer_group in transfer_groups:
            CCApi.transfer_host_module(
                {
                    "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                    "bk_host_id": transfer_group["bk_host_id"],
                    "bk_module_id": [transfer_group["bk_module_id"]],
                    "is_increment": False,
                },
                use_admin=True,
            )

    @classmethod
    def transfer_machines_idle(cls, ips: list):
        """
        DBA业务，将机器转移到空闲机模块
        """
        machines = Machine.objects.filter(ip__in=ips)
        bk_host_ids = [m.bk_host_id for m in machines]
        CCApi.transfer_host_to_idlemodule({"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "bk_host_id": bk_host_ids})

    @classmethod
    def transfer_host_module(cls, bk_host_ids: list, target_module_ids: list):
        """
        跨业务转移主机，需要先做中转处理
        循环判断处理，逻辑保证幂等操作
        """

        if not bk_host_ids:
            # 有些角色允许为空，所以要忽略
            return

        # 查询当前bk_hosts_ids的业务对应关系
        logger.info(f"bk_host_ids:{bk_host_ids}")
        hosts = CCApi.find_host_biz_relations({"bk_host_id": bk_host_ids})

        biz_internal_module = CCApi.get_biz_internal_module({"bk_biz_id": env.DBA_APP_BK_BIZ_ID}, use_admin=True)

        for host in hosts:
            # 根据查询出来当前的host关系信息，做处理

            if env.DBA_APP_BK_BIZ_ID != host["bk_biz_id"]:
                free_bk_module_id = int(SystemSettings.get_setting_value(FREE_BK_MODULE_ID, default="0"))
                if free_bk_module_id == 0:
                    # 获取dba空闲机模块的bk_module_id
                    for module in biz_internal_module["module"]:
                        if module["default"] == IDLE_HOST_MODULE:
                            free_bk_module_id = module["bk_module_id"]

                    SystemSettings.insert_setting_value(FREE_BK_MODULE_ID, free_bk_module_id)

                # 从业务挪到dba空闲机模块下
                CCApi.transfer_host_across_biz(
                    {
                        "src_bk_biz_id": int(host["bk_biz_id"]),
                        "dst_bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                        "bk_host_id": [int(host["bk_host_id"])],
                        "bk_module_id": free_bk_module_id,
                        "is_increment": False,
                    },
                    use_admin=True,
                )

            # 主机转移到对应的模块下，机器可能对应多个集群，所有主机转移到多个模块下是合理的
            CCApi.transfer_host_module(
                {
                    "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                    "bk_host_id": [int(host["bk_host_id"])],
                    "bk_module_id": target_module_ids,
                    "is_increment": False,
                },
                use_admin=True,
            )
