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
from backend.db_services.ipchooser import constants
from backend.db_services.ipchooser.handlers.base import BaseHandler
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper


class TopoCacheManager:
    """缓存管理器"""

    @classmethod
    def get_cached_topo(cls, bk_biz_id, bk_cloud_id=None, bk_biz_name=""):
        """更新缓存，或直接从缓存拿"""

        return cls.cache_idle_topo(bk_biz_id, bk_biz_name, bk_cloud_id)

    @classmethod
    def cache_idle_topo(cls, bk_biz_id, bk_biz_name, bk_cloud_id=None):
        """缓存idle拓扑"""

        idle_set = ResourceQueryHelper.get_biz_internal_module(bk_biz_id)

        idle_topo = {
            "object_name": constants.ObjectType.get_member_value__alias_map().get(constants.ObjectType.SET.value, ""),
            "object_id": constants.ObjectType.SET.value,
            "instance_id": idle_set["bk_set_id"],
            "instance_name": idle_set["bk_set_name"],
            "meta": BaseHandler.get_meta_data(bk_biz_id),
            "child": [],
        }
        idle_node = {
            "bk_biz_id": bk_biz_id,
            "bk_obj_id": constants.ObjectType.SET,
            "bk_inst_id": idle_set["bk_set_id"],
        }

        for internal_module in idle_set.get("module") or []:
            if not internal_module["default"] == constants.IDLE_HOST_MODULE:
                continue

            idle_node.update(
                {
                    "bk_obj_id": constants.ObjectType.MODULE.value,
                    "bk_inst_id": internal_module["bk_module_id"],
                }
            )

            resp = ResourceQueryHelper.query_cc_hosts(
                tree_node=idle_node, fields=["bk_host_id"], bk_cloud_id=bk_cloud_id
            )

            idle_count = resp["count"]
            idle_topo["count"] = idle_count
            idle_topo["child"].append(
                {
                    "object_name": constants.ObjectType.get_member_value__alias_map().get(
                        constants.ObjectType.MODULE.value, ""
                    ),
                    "object_id": constants.ObjectType.MODULE.value,
                    "instance_id": internal_module["bk_module_id"],
                    "instance_name": internal_module["bk_module_name"],
                    "meta": BaseHandler.get_meta_data(bk_biz_id),
                    "count": idle_count,
                    "child": [],
                }
            )

        # 直接展示空闲机模块
        return idle_topo["child"][0]
