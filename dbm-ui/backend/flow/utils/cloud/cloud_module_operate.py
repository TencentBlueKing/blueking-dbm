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
from typing import Dict, List

from django.utils.translation import ugettext as _

from backend import env
from backend.components import CCApi
from backend.db_services.ipchooser.constants import DB_MANAGE_SET
from backend.flow.consts import CloudServiceModuleName

logger = logging.getLogger("flow")


class CloudModuleHandler:
    """云区域服务相关机器转模块操作类"""

    @classmethod
    def get_or_create_set(cls, bk_biz_id: int, bk_set_name: str) -> int:
        """
        获取集群id(默认所有云区域组件管理的的集群名都是一样的，并且集群唯一)
        @param bk_biz_id: 业务ID
        @param bk_set_name: 集群名
        """

        res = CCApi.search_set(
            params={
                "bk_biz_id": bk_biz_id,
                "fields": ["bk_set_name", "bk_set_id"],
                "condition": {"bk_set_name": bk_set_name},
            },
            use_admin=True,
        )

        if res["count"] > 0:
            return res["info"][0]["bk_set_id"]

        res = CCApi.create_set(
            params={
                "bk_biz_id": bk_biz_id,
                "data": {
                    "bk_parent_id": bk_biz_id,
                    "bk_set_name": bk_set_name,
                },
            },
            use_admin=True,
        )
        return res["bk_set_id"]

    @classmethod
    def get_or_create_module(cls, bk_biz_id: int, bk_set_id: int, bk_module_name: str) -> int:
        """
        获取模块id(不同组件属于到不同的模块)
        @param bk_biz_id: 业务ID
        @param bk_set_id: 集群ID
        @param bk_module_name: 模块名字
        """

        res = CCApi.search_module(
            {
                "bk_biz_id": bk_biz_id,
                "bk_set_id": bk_set_id,
                "condition": {"bk_module_name": bk_module_name},
            },
            use_admin=True,
        )

        if res["count"] > 0:
            return res["info"][0]["bk_module_id"]

        res = CCApi.create_module(
            {
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "bk_set_id": bk_set_id,
                "data": {"bk_parent_id": bk_set_id, "bk_module_name": bk_module_name},
            },
            use_admin=True,
        )
        return res["bk_module_id"]

    @classmethod
    def find_cloud_module_host_relation(cls, bk_biz_id: int, bk_set_id: int) -> Dict[int, List]:
        """
        查询主机与模块之间的关系
        @param bk_biz_id: 业务ID
        @param bk_set_id: 集群ID
        """

        find_module_params = {
            "bk_biz_id": bk_biz_id,
            "bk_set_ids": [bk_set_id],
            "fields": ["bk_module_id", "bk_module_name"],
        }
        res = CCApi.find_module_with_relation(find_module_params, use_admin=True)
        cloud_module_ids = [module["bk_module_id"] for module in res["info"]]

        find_module_hosts_params = {
            "bk_biz_id": bk_biz_id,
            "bk_module_ids": cloud_module_ids,
            "module_fields": ["bk_module_id"],
            "host_fields": ["bk_host_id"],
            "page": {
                # TODO: 暂时认为一个业务下的云区域部署机器不会超过1000台
                "limit": 1000
            },
        }
        res = CCApi.find_module_host_relation(find_module_hosts_params, use_admin=True)
        host_id__module_ids_map: Dict[int, List] = {}
        for relation in res["relation"]:
            module_ids = [info["bk_module_id"] for info in relation["modules"]]
            host_id__module_ids_map[relation["host"]["bk_host_id"]] = module_ids

        return host_id__module_ids_map

    @classmethod
    def _transfer_hosts_in_modules(cls, bk_biz_id, bk_module_ids, bk_host_ids, is_increment=False):
        transfer_params = {
            "bk_biz_id": bk_biz_id,
            "bk_host_id": bk_host_ids,
            "bk_module_id": bk_module_ids,
            "is_increment": is_increment,
        }
        res = CCApi.transfer_host_module(transfer_params, use_admin=True, raw=True)

        if not res["result"]:
            logger.error(
                _("主机{}转移{}失败，转移参数:{}, 错误信息:{}").format(bk_host_ids, bk_module_ids, transfer_params, res["message"])
            )

    @classmethod
    def transfer_hosts_in_cloud_module(
        cls, bk_biz_id: int, bk_module_name: CloudServiceModuleName, bk_host_ids: List[int]
    ) -> None:
        """
        将机器转移到对应模块中
        @param bk_biz_id: 业务ID
        @param bk_module_name: 模块名称
        @param bk_host_ids: 转移主机的ID列表
        """

        bk_set_id = cls.get_or_create_set(bk_biz_id=bk_biz_id, bk_set_name=DB_MANAGE_SET)
        transfer_module_id = cls.get_or_create_module(
            bk_biz_id=bk_biz_id, bk_set_id=bk_set_id, bk_module_name=bk_module_name
        )
        # 获取所有主机并集的module_id，这样可以避免模块的转移覆盖(因为有可能A主机即属于DRS服务又属于DBHA服务)
        host_id__module_ids_map = cls.find_cloud_module_host_relation(bk_biz_id, bk_set_id)
        for host_id in bk_host_ids:
            cls._transfer_hosts_in_modules(
                bk_biz_id=bk_biz_id,
                bk_module_ids=[*host_id__module_ids_map.get(host_id, []), transfer_module_id],
                bk_host_ids=[host_id],
                is_increment=False,
            )

    @classmethod
    def remove_host_from_origin_module(cls, bk_biz_id: int, bk_module_name: str, bk_host_ids: List[int]):
        """
        移除主机所在模块，若主机不属于任何模块，则将主机挪动到待回收模块
        @param bk_biz_id: 业务ID
        @param bk_module_name: 待删除的模块名
        @param bk_host_ids: 转移主机的ID列表
        """
        bk_set_id = cls.get_or_create_set(bk_biz_id=bk_biz_id, bk_set_name=DB_MANAGE_SET)
        host_id__module_ids_map = cls.find_cloud_module_host_relation(bk_biz_id, bk_set_id)
        origin_module_id = cls.get_or_create_module(
            bk_biz_id=bk_biz_id, bk_set_id=bk_set_id, bk_module_name=bk_module_name
        )
        recycle_host_ids = []
        for host_id in bk_host_ids:
            # 如果只属于一个模块，则直接挪到待回收
            if len(host_id__module_ids_map[host_id]) == 1 and origin_module_id in host_id__module_ids_map[host_id]:
                recycle_host_ids.append(host_id)
            # 否则剔除该模块的隶属
            else:
                host_id__module_ids_map[host_id].remove(origin_module_id)
                cls._transfer_hosts_in_modules(
                    bk_biz_id=bk_biz_id,
                    bk_module_ids=host_id__module_ids_map[host_id],
                    bk_host_ids=[host_id],
                    is_increment=False,
                )

        # 将主机挪到待回收
        res = CCApi.transfer_host_to_recyclemodule(
            {"bk_biz_id": bk_biz_id, "bk_host_id": recycle_host_ids}, use_admin=True, raw=True
        )
        if not res["result"]:
            logger.error(_("主机{}转移待回收失败，错误信息:{}").format(recycle_host_ids, res["message"]))
