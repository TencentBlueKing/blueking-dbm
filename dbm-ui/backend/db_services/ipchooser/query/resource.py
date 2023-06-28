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
import json
import logging
import typing
from json import JSONDecodeError
from typing import Any, Dict, List, Union

from django.core.cache import cache
from django.utils.translation import ugettext as _

from backend.bk_web.constants import CACHE_1D
from backend.components import CCApi
from backend.components.gse.client import GseApi
from backend.utils.batch_request import batch_request
from backend.utils.cache import func_cache_decorator

from .. import constants, exceptions, types
from ..constants import IDLE_HOST_MODULE

logger = logging.getLogger("app")


class ResourceQueryHelper:
    @staticmethod
    def get_biz_internal_module(bk_biz_id):
        """缓存1天内部模块信息"""

        idle_set_key = f"idle_set_{bk_biz_id}"
        idle_set = cache.get(idle_set_key)
        try:
            if idle_set:
                return json.loads(idle_set)
        except JSONDecodeError:
            pass

        idle_set = CCApi.get_biz_internal_module({"bk_biz_id": bk_biz_id}, use_admin=True)
        cache.set(idle_set_key, json.dumps(idle_set), CACHE_1D)
        return idle_set

    @staticmethod
    def get_idle_set_module(bk_biz_id):
        """获取业务内部拓扑信息"""

        idle_set = ResourceQueryHelper.get_biz_internal_module(bk_biz_id)
        idle_set_id = idle_set["bk_set_id"]
        idle_module_id = None
        for internal_module in idle_set.get("module") or []:
            if internal_module["default"] == IDLE_HOST_MODULE:
                idle_module_id = internal_module["bk_module_id"]
                break

        return idle_set_id, idle_module_id

    @staticmethod
    def fetch_biz_list(bk_biz_ids: typing.Optional[typing.List[int]] = None) -> typing.List[typing.Dict]:
        """
        查询业务列表
        :param bk_biz_ids: 业务 ID 列表
        :return: 列表 ，包含 业务ID、名字、业务运维
        """
        search_business_params = {
            # "no_request": True,
            "fields": ["bk_biz_id", "bk_biz_name", "bk_biz_maintainer"],
        }
        biz_infos: typing.List[typing.Dict] = CCApi.search_business(search_business_params)["info"]
        if not bk_biz_ids:
            return biz_infos

        # 转为 set，避免 n^2 查找
        bk_biz_ids: typing.Set[int] = set(bk_biz_ids)
        return [biz_info for biz_info in biz_infos if biz_info["bk_biz_id"] in bk_biz_ids]

    @staticmethod
    def get_topo_tree(bk_biz_id: int, return_all=False) -> types.TreeNode:
        from ..handlers.base import BaseHandler

        internal_set_info: typing.Dict = CCApi.get_biz_internal_module({"bk_biz_id": bk_biz_id}, use_admin=True)
        internal_topo: typing.Dict = {
            "bk_obj_name": constants.ObjectType.get_member_value__alias_map().get(constants.ObjectType.SET.value, ""),
            "bk_obj_id": constants.ObjectType.SET.value,
            "bk_inst_id": internal_set_info["bk_set_id"],
            "bk_inst_name": internal_set_info["bk_set_name"],
            "meta": BaseHandler.get_meta_data(bk_biz_id),
            "child": [],
        }

        for internal_module in internal_set_info.get("module") or []:
            internal_topo["child"].append(
                {
                    "bk_obj_name": constants.ObjectType.get_member_value__alias_map().get(
                        constants.ObjectType.MODULE.value, ""
                    ),
                    "bk_obj_id": constants.ObjectType.MODULE.value,
                    "bk_inst_id": internal_module["bk_module_id"],
                    "bk_inst_name": internal_module["bk_module_name"],
                    "meta": BaseHandler.get_meta_data(bk_biz_id),
                    "child": [],
                }
            )

        if return_all:
            try:
                topo_tree: types.TreeNode = CCApi.search_biz_inst_topo({"bk_biz_id": bk_biz_id, "no_request": True})[0]
            except IndexError:
                logger.error(f"topo not exists, bk_biz_id -> {bk_biz_id}")
                raise exceptions.TopoNotExistsError({"bk_biz_id": bk_biz_id})

            # 补充空闲机拓扑
            topo_tree["child"] = [internal_topo] + topo_tree.get("child") or []
            return topo_tree

        return internal_topo

    @staticmethod
    def fetch_host_topo_relations(bk_biz_id: int) -> typing.List[typing.Dict]:
        host_topo_relations: typing.List[typing.Dict] = batch_request(
            func=CCApi.find_host_topo_relation,
            params={"bk_biz_id": bk_biz_id, "no_request": True},
            get_data=lambda x: x["data"],
        )
        return host_topo_relations

    @staticmethod
    def query_cc_hosts(
        tree_node: types.TreeNode,
        conditions: typing.List[types.Condition] = None,
        start: int = 0,
        page_size: int = 1000,
        fields: typing.List[str] = constants.CommonEnum.DEFAULT_HOST_FIELDS.value,
        return_status: bool = False,
        bk_cloud_id: int = None,
    ) -> typing.Dict:
        """
        查询主机
        :param tree_node: 拓扑节点
        :param conditions: 查询条件
        :param bk_cloud_id: 过滤主机的云区域ID
        :param fields: 字段
        :param start: 数据起始位置
        :param page_size: 拉取数据数量
        :param return_status: 返回agent状态
        :return:
        """

        instance_id = tree_node["bk_inst_id"]
        object_id = tree_node["bk_obj_id"]

        params = {
            "bk_biz_id": tree_node["bk_biz_id"],
            "fields": fields,
            "page": {"start": start, "limit": page_size, "sort": "bk_host_innerip"},
        }

        # 云区域过滤
        if bk_cloud_id is not None:
            params.update(
                {
                    "host_property_filter": {
                        "condition": "AND",
                        "rules": [{"field": "bk_cloud_id", "operator": "equal", "value": bk_cloud_id}],
                    }
                }
            )

        # rules不能为空
        if conditions:
            if bk_cloud_id is None:
                params.update({"host_property_filter": {"condition": "OR", "rules": conditions}})
            else:
                params["host_property_filter"]["rules"].append({"condition": "OR", "rules": conditions})

        if object_id == "module":
            params.update(bk_module_ids=[instance_id])

        if object_id == "set":
            params.update(bk_set_ids=[instance_id])

        # 获取主机信息
        resp = CCApi.list_biz_hosts(params, use_admin=True)

        if resp["info"] and return_status:
            ResourceQueryHelper.fill_agent_status(resp["info"])

        return resp

    @staticmethod
    def fill_agent_status(cc_hosts, fill_key="status"):

        if not cc_hosts:
            return

        index = 0
        hosts, host_map = [], {}
        for cc_host in cc_hosts:
            ip, bk_cloud_id = cc_host["bk_host_innerip"], cc_host["bk_cloud_id"]
            hosts.append({"ip": ip, "bk_cloud_id": bk_cloud_id})

            host_map[f"{bk_cloud_id}:{ip}"] = index
            index += 1

        try:
            status_map = GseApi.get_agent_status({"hosts": hosts})

            for ip_cloud, detail in status_map.items():
                cc_hosts[host_map[ip_cloud]][fill_key] = detail["bk_agent_alive"]
        except KeyError as e:
            logger.error("fill_agent_status exception: %s", e)

    @staticmethod
    def fill_cloud_name(cc_hosts):
        if not cc_hosts:
            return

        # 补充云区域名称
        resp = CCApi.search_cloud_area({"page": {"start": 0, "limit": 1000}})

        cloud_map = (
            {cloud_info["bk_cloud_id"]: cloud_info["bk_cloud_name"] for cloud_info in resp["info"]}
            if resp.get("info")
            else {}
        )

        for host in cc_hosts:
            host["bk_cloud_name"] = cloud_map.get(host["bk_cloud_id"], host["bk_cloud_id"])

    @staticmethod
    def query_host_topo_infos(
        bk_biz_id: int,
        filter_conditions: Dict[str, Any],
        host_property_filter: Dict = None,
        start: int = 0,
        limit: int = 500,
    ) -> List[Dict]:
        """
        获取主机的拓扑信息
        :param bk_biz_id: 业务ID
        :param filter_conditions: 过滤字典，过滤条件默认为AND
        :param host_property_filter: 主机属性字段过滤规则，过滤规则同cc
        :param start: 起始位置
        :param limit: 获取数量
        """

        def _get_host_topo(_host_topo: List[Dict[str, Any]]) -> List[str]:
            """
            根据拓扑字典平铺获取平铺拓扑信息列表
            :param _host_topo: 主机拓扑信息
            """

            if not _host_topo:
                return [""]

            _host_topo_info_list = []
            for topo in _host_topo:
                level_name = topo["inst"]["name"]
                children_topo = _get_host_topo(topo["children"])
                _host_topo_info_list.extend([f"{level_name}/{child_topo}" for child_topo in children_topo])

            return _host_topo_info_list

        def _parse_host_filter(_host: str) -> Dict:
            """
            根据主机字段获取格式化主机过滤信息
            :param _host: (cloud_id:)ip
            """
            _bk_cloud_id, _ip = _host.split(":") if ":" in _host else (None, _host)
            if _bk_cloud_id:
                _host_filters = {
                    "condition": "AND",
                    "rules": [
                        {"field": "bk_cloud_id", "operator": "equal", "value": int(_bk_cloud_id)},
                        {"field": "bk_host_innerip", "operator": "equal", "value": _ip},
                    ],
                }
            else:
                _host_filters = {"field": "bk_host_innerip", "operator": "equal", "value": _ip}

            return _host_filters

        if not host_property_filter:
            host_property_filter = {"condition": "AND", "rules": []}

        # 如果有主机过滤字段，则提前查询，防止host_property_filter嵌套过深
        if "bk_host_innerip" in filter_conditions.keys():
            ip_rules = [_parse_host_filter(host) for host in filter_conditions["bk_host_innerip"]]
            ip_rules = {"condition": "OR", "rules": ip_rules}
            params = {
                "bk_biz_id": bk_biz_id,
                "page": {"start": 0, "limit": limit, "sort": "bk_host_id"},
                "host_property_filter": ip_rules,
                "fields": ["bk_host_id"],
            }
            res = CCApi.list_biz_hosts(params=params, use_admin=True)

            # 移除bk_host_innerip的查询，改用bk_host_id查询
            filter_conditions.pop("bk_host_innerip")
            filter_conditions["bk_host_id"] = [host["bk_host_id"] for host in res["info"]]

        # 如果有模块过滤条件，则创建module_property_filter
        module_property_filter: Dict[str, Any] = {}
        mode = filter_conditions.pop("mode", None)
        if mode == constants.ModeType.IDLE_ONLY.value:
            _, idle_module_id = ResourceQueryHelper.get_idle_set_module(bk_biz_id)
            module_property_filter = {
                "condition": "AND",
                "rules": [{"field": "bk_module_id", "operator": "equal", "value": idle_module_id}],
            }

        # 获取过滤条件
        rules: List[Dict[str, Any]] = []
        for field, filter_value in filter_conditions.items():
            if isinstance(filter_value, str):
                rules.append({"field": field, "operator": "in", "value": filter_value})
            elif isinstance(filter_value, list):
                rules.append({"field": field, "operator": "in", "value": filter_value})
            else:
                rules.append({"field": field, "operator": "equal", "value": filter_value})

        host_property_filter["rules"].extend(rules)
        fields = ["bk_host_id", "bk_host_innerip", "bk_cloud_id"]

        # 获取主机的拓扑信息
        list_host_total_mainline_topo_filter = {
            "bk_biz_id": bk_biz_id,
            "fields": fields,
            "host_property_filter": host_property_filter,
            "page": {"start": start, "limit": limit},
        }
        if module_property_filter:
            list_host_total_mainline_topo_filter["module_property_filter"] = module_property_filter

        resp = CCApi.list_host_total_mainline_topo(list_host_total_mainline_topo_filter)

        # 格式化主机信息，铺平拓扑信息
        host_topo_info_list: List[Dict[str, Any]] = []
        for host_topo in resp["info"]:
            host_topo_info = host_topo["host"]
            host_topo_info["ip"] = host_topo_info.pop("bk_host_innerip")
            host_topo_info.update({"topo": _get_host_topo(_host_topo=host_topo["topo"])})
            host_topo_info_list.append(host_topo_info)

        return host_topo_info_list

    @staticmethod
    def search_cc_hosts(
        bk_biz_id: int,
        role_host_ids: List[int],
        keyword: str = None,
        set_filter: Union[str, List] = None,
        module_filter: Union[str, List] = None,
    ):
        """
        搜索主机
        :param bk_biz_id: 业务ID
        :param role_host_ids: 过滤的主机ID列表
        :param keyword: 过滤关键字，主要用于host_property_filter
        :param set_filter: 集群过滤条件，为set_cond和bk_set_ids二者之一，
        若是set_cond则set_filter为str，支持eq运算符；若是bk_set_ids，则set_filter为List[int]。
        :param module_filter: 模块过滤条件，同set_filter
        """

        def _split_keyword(_keyword: str) -> List:
            # 获取过滤参数,支持逗号或者空格分隔
            if _keyword:
                _keyword_list = keyword.split(",") if "," in keyword else keyword.split()
            else:
                _keyword_list = None

            return _keyword_list

        if not role_host_ids:
            return []

        # 生成主机过滤条件
        rules = [{"field": "bk_host_id", "operator": "in", "value": role_host_ids}]
        limit = len(role_host_ids)

        # 主机的集群过滤条件
        set_filter_field = None
        if isinstance(set_filter, str):
            set_filter_field = "set_cond"
            set_filter = [{"field": "bk_set_name", "operator": "$eq", "value": set_filter}]
        elif isinstance(set_filter, list):
            set_filter_field = "bk_set_ids"
            set_filter = [int(set_id) for set_id in set_filter]

        # 主机的模块过滤条件
        module_filter_field = None
        if isinstance(module_filter, str):
            module_filter_field = "module_cond"
            module_filter = [{"field": "bk_module_name", "operator": "$eq", "value": module_filter}]
        elif isinstance(module_filter, list):
            module_filter_field = "bk_module_ids"
            module_filter = [int(module_id) for module_id in module_filter]

        keyword_list = _split_keyword(keyword)
        if keyword_list:
            rules.append(
                {
                    "condition": "OR",
                    "rules": [
                        {"field": field, "operator": "contains", "value": key}
                        for key in keyword_list
                        for field in ["bk_host_name", "bk_host_innerip"]
                    ],
                }
            )

        list_biz_hosts_filter = {
            "bk_biz_id": bk_biz_id,
            "fields": [
                "bk_host_id",
                "bk_host_innerip",
                "bk_host_innerip_v6",
                "bk_cloud_id",
                "bk_host_name",
                "bk_os_name",
                "bk_os_type",
                "bk_agent_id",
                "bk_cloud_vendor",
                "bk_mem",
                "bk_cpu",
                "bk_disk",
                "bk_machine_type",
                "bk_module_name",
            ],
            "page": {"start": 0, "limit": limit, "sort": "bk_host_innerip"},
            "host_property_filter": {"condition": "AND", "rules": rules},
        }
        if set_filter_field:
            list_biz_hosts_filter.update({set_filter_field: set_filter})

        if module_filter_field:
            list_biz_hosts_filter.update({module_filter_field: module_filter})

        # 获取主机信息
        resp = CCApi.list_biz_hosts(list_biz_hosts_filter, use_admin=True)
        hosts = resp["info"]

        ResourceQueryHelper.fill_agent_status(hosts)
        ResourceQueryHelper.fill_cloud_name(hosts)

        return hosts

    @classmethod
    @func_cache_decorator(cache_time=60 * 60)
    def search_cc_cloud(cls, fields=None):
        """
        查询云区域信息
        """

        resp = batch_request(
            func=CCApi.search_cloud_area,
            params={},
            get_data=lambda x: x["info"],
        )
        cloud_id__cloud_info = {
            str(info["bk_cloud_id"]): {f: info[f] for f in fields} if fields else info for info in resp
        }
        # 命名要求 default_area ---> Direct Mode
        cloud_id__cloud_info[str(0)]["bk_cloud_name"] = _("直连区域")
        return cloud_id__cloud_info
