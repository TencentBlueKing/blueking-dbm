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

from backend.utils.batch_request import batch_decorator

from .. import constants, types
from ..query.resource import ResourceQueryHelper
from ..tools import topo_tool
from .base import BaseHandler

logger = logging.getLogger("app")


class TopoHandler:
    @staticmethod
    def format2tree_node(node: types.ReadableTreeNode) -> types.TreeNode:
        return {
            "bk_obj_id": node["object_id"],
            "bk_inst_id": node["instance_id"],
            "bk_biz_id": node["meta"]["bk_biz_id"],
        }

    @staticmethod
    def format_tree(topo_tree: types.TreeNode) -> types.ReadableTreeNode:
        bk_biz_id: int = topo_tree["meta"]["bk_biz_id"]
        topo_tree_stack: typing.List[types.TreeNode] = [topo_tree]

        # 定义一个通过校验的配置根节点及栈结构，同步 topo_tree_stack 进行遍历写入
        formatted_topo_tree: types.ReadableTreeNode = {}
        formatted_topo_tree_stack: typing.List[types.ReadableTreeNode] = [formatted_topo_tree]

        # 空间换时间，迭代模拟递归
        while topo_tree_stack:
            # 校验节点
            node = topo_tree_stack.pop()
            # 与 topo_tree_stack 保持相同的遍历顺序，保证构建拓扑树与给定的一致
            formatted_node = formatted_topo_tree_stack.pop()
            formatted_node.update(
                {
                    "instance_id": node["bk_inst_id"],
                    "instance_name": node["bk_inst_name"],
                    "object_id": node["bk_obj_id"],
                    "object_name": node["bk_obj_name"],
                    "meta": BaseHandler.get_meta_data(bk_biz_id),
                    "count": node.get("count", 0),
                    "child": [],
                    "expanded": True,
                }
            )
            child_nodes = node.get("child", [])
            topo_tree_stack.extend(child_nodes)
            formatted_node["child"] = [{} for __ in range(len(child_nodes))]
            formatted_topo_tree_stack.extend(formatted_node["child"])

        return formatted_topo_tree

    @classmethod
    def trees(cls, all_scope: bool, scope_list: types.ScopeList, mode: str = "all") -> typing.List[typing.Dict]:
        """
        拓扑树
        """

        # 多业务支持，暂不需要，待产品形态最终确认后移除
        if all_scope and len(scope_list) == 0:
            return topo_tool.TopoTool.get_all_scope_topo_with_count()

        # 空闲拓扑
        if mode == constants.ModeType.IDLE_ONLY.value:
            return topo_tool.TopoTool.get_idle_topo_tree_with_count(
                scope_list[0]["bk_biz_id"], bk_cloud_id=scope_list[0].get("bk_cloud_id")
            )

        # 全部拓扑
        return [cls.format_tree(topo_tool.TopoTool.get_topo_tree_with_count(scope_list[0]["bk_biz_id"]))]

    @classmethod
    @batch_decorator(
        is_classmethod=True,
        start_key="start",
        limit_key="page_size",
        get_data=lambda x: x["data"],
        get_count=lambda x: x["total"],
    )
    def query_hosts(
        cls,
        readable_node_list: typing.List[types.ReadableTreeNode],
        conditions: typing.List[types.Condition],
        page: typing.Dict[str, int],
        fields: typing.List[str] = constants.CommonEnum.DEFAULT_HOST_FIELDS.value,
        mode: str = constants.ModeType.ALL.value,
        bk_cloud_id: int = None,
    ) -> typing.Dict:
        """
        查询主机
        :param readable_node_list: 拓扑节点
        :param conditions: 查询条件
        :param fields: 字段
        :param page: 分页参数, start和page_size
        :param mode: all（全部）/idle_only（空闲机）
        :param bk_cloud_id: 云区域id
        :return:
        """

        # 不存在查询节点提前返回，减少非必要 IO
        if not readable_node_list:
            return {"total": 0, "data": []}

        tree_node: types.TreeNode = cls.format2tree_node(readable_node_list[0])

        # 范围锁定为空闲机
        if mode == constants.ModeType.IDLE_ONLY.value:
            _, idle_module_id = ResourceQueryHelper.get_idle_set_module(tree_node["bk_biz_id"])
            tree_node.update(
                {
                    "bk_obj_id": constants.ObjectType.MODULE.value,
                    "bk_inst_id": idle_module_id,
                }
            )

        # 获取主机信息
        start, page_size = page["start"], page["page_size"]
        resp = ResourceQueryHelper.query_cc_hosts(
            tree_node, conditions, start, page_size, fields, return_status=True, bk_cloud_id=bk_cloud_id
        )

        return {"total": resp["count"], "data": BaseHandler.format_hosts(resp["info"], tree_node["bk_biz_id"])}

    @classmethod
    def query_host_id_infos(
        cls,
        readable_node_list: typing.List[types.ReadableTreeNode],
        conditions: typing.List[types.Condition],
        start: int,
        page_size: int,
    ) -> typing.Dict:
        """
        查询主机 ID 信息
        :param readable_node_list: 拓扑节点
        :param conditions: 查询条件
        :param start: 数据起始位置
        :param page_size: 拉取数据数量
        :return:
        """
        if not readable_node_list:
            return {"total": 0, "data": []}

        tree_node: types.TreeNode = cls.format2tree_node(readable_node_list[0])

        # TODO: 支持全量查询
        page_size = page_size if page_size > 0 else 1000
        resp = ResourceQueryHelper.query_cc_hosts(
            tree_node,
            conditions,
            start,
            page_size,
            ["bk_host_id", "bk_host_innerip", "bk_host_innerip_v6", "bk_cloud_id"],
        )

        return {"total": resp["count"], "data": BaseHandler.format_host_id_infos(resp["info"], tree_node["bk_biz_id"])}

    @classmethod
    def query_host_topo_infos(
        cls, bk_biz_id: int, filter_conditions: typing.Dict, start: int, page_size: int
    ) -> typing.Dict:
        """
        根据过滤条件查询主机拓扑信息(目前仅支持ip，后续可拓展)
        :param bk_biz_id: 业务ID
        :param filter_conditions: 过滤条件
        :param start: 数据起始位置
        :param page_size: 拉取数据数量
        """

        page_size = page_size if page_size > 0 else 500
        hosts_topo_info = ResourceQueryHelper.query_host_topo_infos(
            bk_biz_id, filter_conditions, start=start, limit=page_size
        )
        return {"total": len(hosts_topo_info), "hosts_topo_info": hosts_topo_info}
