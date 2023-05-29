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
import typing
from collections import defaultdict

from django.core.cache import cache

from .. import constants, types
from ..handlers.base import BaseHandler
from ..models import TopoCacheManager
from ..query import resource

logger = logging.getLogger("app")


class TopoTool:
    CACHE_5MIN = 5 * 60

    @classmethod
    def fill_host_count_to_tree(
        cls, nodes: typing.List[types.TreeNode], host_ids_gby_module_id: typing.Dict[int, typing.List[int]]
    ) -> typing.Set[int]:
        total_host_ids: typing.Set[int] = set()
        for node in nodes:
            bk_host_ids: typing.Set[int] = set()
            if node.get("bk_obj_id") == constants.ObjectType.MODULE.value:
                bk_host_ids = bk_host_ids | set(host_ids_gby_module_id.get(node["bk_inst_id"], set()))
            else:
                bk_host_ids = cls.fill_host_count_to_tree(node.get("child", []), host_ids_gby_module_id)
            node["count"] = len(bk_host_ids)
            total_host_ids = bk_host_ids | total_host_ids
        return total_host_ids

    @classmethod
    def get_topo_tree_with_count(cls, bk_biz_id: int, return_all: bool = True) -> types.TreeNode:
        topo_tree: types.TreeNode = resource.ResourceQueryHelper.get_topo_tree(bk_biz_id, return_all=return_all)

        # 这个接口较慢，缓存5min
        cache_key = f"host_topo_relations:{bk_biz_id}"
        host_topo_relations: typing.List[typing.Dict] = cache.get(cache_key)
        if not host_topo_relations:
            host_topo_relations = resource.ResourceQueryHelper.fetch_host_topo_relations(bk_biz_id)
            cache.set(cache_key, host_topo_relations, cls.CACHE_5MIN)

        host_ids_gby_module_id: typing.Dict[int, typing.List[int]] = defaultdict(list)
        for host_topo_relation in host_topo_relations:
            bk_host_id: int = host_topo_relation["bk_host_id"]

            # 暂不统计非缓存数据，遇到不一致的情况需要触发缓存更新
            host_ids_gby_module_id[host_topo_relation["bk_module_id"]].append(bk_host_id)
        cls.fill_host_count_to_tree([topo_tree], host_ids_gby_module_id)

        topo_tree.update({"meta": BaseHandler.get_meta_data(bk_biz_id)})

        return topo_tree

    @classmethod
    def get_idle_topo_tree_with_count(cls, bk_biz_id: int, bk_cloud_id: int = None):
        """获取业务空闲机拓扑"""
        topo_tree = TopoCacheManager.get_cached_topo(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id)
        return [topo_tree]
