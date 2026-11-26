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
from typing import Any, Callable, Dict, List

from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from backend.components.kubernetes.client import KubernetesApi
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, Tag
from backend.db_services.dbbase.resources import query
from backend.db_services.dbbase.resources.query import CommonExportQueryResourceMixin, ResourceList
from backend.db_services.kubernetes.utils import offset_to_page, parse_deploy_params
from backend.ticket.constants import TicketType


def _split_multi_value(value: str) -> List[str]:
    """解析逗号分隔的多值查询参数"""
    return value.split(",") if value else []


class KubernetesBaseExportQueryResourceMixin(CommonExportQueryResourceMixin):
    """补充k8s集群列表导出所需的header及数据父类"""

    @classmethod
    def update_headers(cls, headers, **kwargs):
        """
        更新的headers列表数据
        """
        filtered_headers = list(filter(lambda header: header["id"] not in ["slave_domain", "db_module_name"], headers))
        extra_headers = kwargs.get("extra_headers", [])
        return filtered_headers, extra_headers

    @classmethod
    def update_cluster_info(cls, cluster, cluster_info, **kwargs):
        """
        更新的集群列表数据
        """
        # 删除cluster_info中的从域名/模块字段值
        del cluster_info["slave_domain"], cluster_info["db_module_name"]
        return cluster_info


class KubernetesBaseListRetrieveResource(query.ListRetrieveResource, KubernetesBaseExportQueryResourceMixin):
    """
    k8s相关组件资详情基类
    """

    cluster_types = []
    instance_roles = []
    # 支持部署模式(共享集群/独占集群)下发的集群类型，不在白名单内的集群类型不下发 isPublic/bkBizId
    deploy_mode_cluster_types = [
        ClusterType.K8sQdrantHa,
        ClusterType.K8sSurrealdbHa,
        ClusterType.K8sSurrealdbSingle,
        ClusterType.K8sVictoriametricsCluster,
        ClusterType.K8sVictoriametricsSelect,
    ]
    fields = [
        {"name": _("集群名"), "key": "cluster_name"},
        {"name": _("集群别名"), "key": "cluster_alias"},
        {"name": _("集群类型"), "key": "cluster_type"},
        {"name": _("集群类型名"), "key": "cluster_type_name"},
        {"name": _("域名"), "key": "domain"},
        {"name": _("版本"), "key": "major_version"},
        {"name": _("创建人"), "key": "creator"},
        {"name": _("创建时间"), "key": "create_at"},
        {"name": _("更新人"), "key": "updater"},
        {"name": _("更新时间"), "key": "update_at"},
    ]

    @classmethod
    def get_topo_graph(
        cls, bk_biz_id: int, cluster_id: int, bcs_cluster_name: str = None, namespace: str = None
    ) -> dict:
        raise NotImplementedError()

    @classmethod
    def _enrich_topo_graph_node_port(cls, graph: dict, port: int) -> dict:
        """
        为拓扑图中入口节点的 node_id 追加 :port 后缀。

        入口节点（node_type 以 "entry_" 开头）的 node_id 会同步改写
        nodes、根 node_id、groups.children_id 以及 lines 的 source/target，
        保证同一节点在各字段中的 id 一致。
        """
        if not port:
            return graph

        # 1. 收集需要追加端口号的节点 ID（入口节点）
        node_ids_to_update: set = set()
        for node in graph.get("nodes", []):
            node_type = node.get("node_type", "")
            node_id = node.get("node_id", "")
            # 入口节点（entry_dns / entry_clb 等）追加端口
            if node_type.startswith("entry_") and node_id:
                node_ids_to_update.add(node_id)

        if not node_ids_to_update:
            return graph

        port_suffix = f":{port}"

        def _with_port(node_id: str) -> str:
            if node_id in node_ids_to_update:
                return f"{node_id}{port_suffix}"
            return node_id

        # 2. 更新 nodes 的 node_id
        for node in graph.get("nodes", []):
            node["node_id"] = _with_port(node.get("node_id", ""))

        # 3. 根 node_id 若指向入口节点，一并追加端口
        graph["node_id"] = _with_port(graph.get("node_id") or "")

        # 4. 更改 groups 里的 children_id
        for group in graph.get("groups", []):
            group["children_id"] = [_with_port(child_id) for child_id in group.get("children_id", [])]

        # 5. 同步 lines 端点，避免 source/target 仍是未加端口的旧 id
        for line in graph.get("lines", []):
            line["source"] = _with_port(line.get("source", ""))
            line["target"] = _with_port(line.get("target", ""))

        return graph

    @classmethod
    def support_deploy_mode(cls) -> bool:
        """当前集群类型是否支持部署模式(共享集群/独占集群)参数下发"""
        return bool(set(cls.cluster_types) & set(cls.deploy_mode_cluster_types))

    @classmethod
    def get_deploy_params(cls, query_params: Dict, bk_biz_id: int = None) -> Dict:
        """提取需要下发到k8s接口的部署模式参数(共享集群/独占集群)

        isPublic: 是否共享集群(True-共享集群/公共集群，False-独占集群)，默认共享集群
        bkBizId: 独占集群所属的业务ID，未显式传入时取当前业务ID
        仅对 deploy_mode_cluster_types 白名单内的集群类型下发，其余(如VM)返回空
        @param query_params: 视图层下发到k8s的查询参数
        @param bk_biz_id: 业务ID
        """
        if not cls.support_deploy_mode():
            return {}
        return parse_deploy_params(query_params, bk_biz_id)

    @classmethod
    def _list_clusters(
        cls,
        bk_biz_id: int,
        query_params: Dict,
        limit: int,
        offset: int,
        filter_params_map: Dict[str, Q] = None,
        filter_func_map: Dict[str, Callable] = None,
        **kwargs,
    ) -> ResourceList:
        kwargs["bk_username"] = query_params.get("bk_username")
        return super()._list_clusters(
            bk_biz_id, query_params, limit, offset, filter_params_map, filter_func_map, **kwargs
        )

    @classmethod
    def _retrieve_cluster(cls, cluster_details: Dict[str, Any], cluster_id: int) -> Dict[str, Any]:
        """集群详情补充 k8s 元数据

        k8s_cluster_name / namespace / components 依赖第三方接口（cluster_detail），
        仅在详情接口返回；列表接口不再逐集群请求，避免 N+1 拖慢列表。
        """
        cluster_details = super()._retrieve_cluster(cluster_details, cluster_id)
        cluster_detail = KubernetesApi.cluster_detail({"cluster_id": cluster_id}, use_admin=True) or {}
        cluster_details.update(
            {
                "k8s_cluster_name": (cluster_detail.get("k8sClusterConfig") or {}).get("clusterName", ""),
                "namespace": cluster_detail.get("namespace", ""),
                "components": (cluster_detail.get("addonInfo") or {}).get("topology", {}).get("components", []),
            }
        )
        return cluster_details

    @classmethod
    def _list_instances(
        cls,
        bk_biz_id: int,
        query_params: Dict,
        limit: int,
        offset: int,
        filter_params_map: Dict[str, Q] = None,
        **kwargs,
    ) -> ResourceList:
        """
        查询实例信息
        @param bk_biz_id: 业务 ID
        @param query_params: 查询条件. 通过 .serializers.ListResourceSLZ 完成数据校验
        @param limit: 分页查询, 每页展示的数目
        @param offset: 分页查询, 当前页的偏移数
        @param filter_params_map: 过滤参数map
        """
        # 解析多值参数（逗号分隔的字符串）：cluster_name / k8s_cluster_name / namespace 按索引一一对应
        cluster_name_list = _split_multi_value(query_params.get("cluster_name", ""))
        # 没有指定集群，不查询（提前返回，避免无意义的 DB 查询）
        if not cluster_name_list:
            return ResourceList(count=0, data=[])

        k8s_cluster_name_list = _split_multi_value(query_params.get("k8s_cluster_name", ""))
        namespace_list = _split_multi_value(query_params.get("namespace", ""))
        if not (len(cluster_name_list) == len(k8s_cluster_name_list) == len(namespace_list)):
            raise ValueError(_("cluster_name, k8s_cluster_name, namespace 参数数量必须一致"))

        # 批量反查 cluster_id，用于权限字段嵌入(viewsets.list_instances 的 id_field=lambda d: d["cluster_id"])
        # 构建 cluster_name -> cluster_id 的映射
        cluster_ids = query_params.get("cluster_id")
        if cluster_ids:
            # 如果传入了 cluster_id，支持多选（只支持逗号分隔的字符串格式）
            clusters = Cluster.objects.filter(bk_biz_id=bk_biz_id, id__in=_split_multi_value(cluster_ids))
        else:
            # 通过集群名反查，支持多选
            clusters = Cluster.objects.filter(bk_biz_id=bk_biz_id, name__in=cluster_name_list)
        cluster_id_map = dict(clusters.values_list("name", "id"))

        # 可选过滤参数，DBS 侧入参统一为驼峰命名
        optional_filters = {
            "componentName": query_params.get("component_name"),
            "status": query_params.get("status"),
            "node": query_params.get("node"),
            "podName": query_params.get("pod_name"),
        }
        component_name = optional_filters["componentName"]

        # 分页：DBS 使用 page/limit，而前端传的是 limit/offset
        # 单集群时直接把分页下发给 DBS（避免全量拉取）；多集群时各集群的 page 无法合并，改为全量拉取后本地切片
        api_paginate = len(cluster_name_list) == 1 and limit > 0

        result = {"count": 0, "data": []}
        for cluster_name, k8s_cluster_name, namespace in zip(cluster_name_list, k8s_cluster_name_list, namespace_list):
            params = {
                "k8sClusterName": k8s_cluster_name,
                "clusterName": cluster_name,
                "namespace": namespace,
                # 空值不下发，避免被 DBS 当成过滤条件
                **{key: value for key, value in optional_filters.items() if value},
            }
            if api_paginate:
                params.update(offset_to_page({"offset": offset, "limit": limit}))

            res = KubernetesApi.component_pods(params, use_admin=True) or {}
            pods = res.get("result") or []
            # DBS 未返回 count 时退化为当前批次条数，避免列表总数为 0
            result["count"] += res.get("count") or len(pods)

            cluster_id = cluster_id_map.get(cluster_name)
            for pod in pods:
                # 给每条 pod 数据补充 cluster_id，供权限装饰器(id_field=lambda d: d["cluster_id"])使用
                pod["cluster_id"] = cluster_id
                # 仅在显式指定组件时覆盖，否则保留 DBS 返回的真实组件名
                if component_name:
                    pod["componentName"] = component_name
            result["data"].extend(pods)

        # 全量拉取场景（多集群 / limit=-1）下，按前端分页参数在本地切片，count 仍为总数
        if not api_paginate and limit > 0:
            result["data"] = result["data"][offset : offset + limit]

        return ResourceList(**result)

    @classmethod
    def retrieve_ins(cls, query_params) -> dict:
        res = KubernetesApi.pod_detail(query_params, use_admin=True)
        return res

    @classmethod
    def get_operation_log(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> ResourceList:
        """查询集群列表，补充公共字段"""
        from backend.ticket.models import Ticket

        query_params = offset_to_page(query_params)
        res = KubernetesApi.cluster_operation_log(query_params, use_admin=True)

        # 获取所有操作日志的 ticket_id
        operation_logs = res.get("result") or []
        ticket_ids = [log.get("ticketId") for log in operation_logs if log.get("ticketId")]
        ticket_ids = list(set(filter(None, ticket_ids)))  # 去重并过滤空值

        # 批量查询 Ticket 信息
        tickets = Ticket.objects.filter(id__in=ticket_ids).values("id", "status", "ticket_type")
        ticket_map = {ticket["id"]: ticket for ticket in tickets}

        # 为每条操作日志补充 ticket_status、ticket_type 和 ticket_type_display 字段
        for log in operation_logs:
            ticket_id = log.get("ticketId")
            if ticket_id and ticket_id in ticket_map:
                ticket = ticket_map[ticket_id]
                log["ticket_status"] = ticket["status"]
                log["ticket_type"] = ticket["ticket_type"]
                # 获取单据类型的中文显示名
                log["ticket_type_display"] = TicketType.get_choice_label(ticket["ticket_type"])
            else:
                log["ticket_status"] = None
                log["ticket_type"] = None
                log["ticket_type_display"] = None

        return ResourceList(count=res.get("count", 0), data=operation_logs)

    @classmethod
    def get_component_spec(cls, query_params):
        res = KubernetesApi.cluster_describe(query_params, use_admin=True)
        return res

    @classmethod
    def get_regions(cls, query_params: Dict = None, bk_biz_id: int = None) -> list:
        """获取可用区域(BCS集群)列表

        支持按部署模式过滤：isPublic=true(默认) 返回共享集群的可用区域，
        isPublic=false 时按 bkBizId 返回独占集群的可用区域
        """
        deploy_params = cls.get_deploy_params(query_params or {}, bk_biz_id)
        return KubernetesApi.bcs_regions(params=deploy_params, use_admin=True)

    @classmethod
    def update_cluster_meta(
        cls,
        bk_biz_id: int,
        cluster_id: int,
        bk_username: str,
        updated_by: str = None,
        cluster_alias: str = None,
        tags: List[Dict] = None,
    ) -> None:
        """
        更新 K8s 集群的别名/标签，并同步到 DBS 端
        """
        from backend.db_meta.enums.comm import TagType

        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)

        if cluster_alias is not None:
            cluster.alias = cluster_alias
            cluster.save(update_fields=["alias"])

        if tags is not None:
            tag_objs = []
            for tag_item in tags:
                (tag_key,) = tag_item.keys()
                (tag_value,) = tag_item.values()
                if not tag_key:
                    continue
                tag, _ = Tag.objects.update_or_create(
                    bk_biz_id=bk_biz_id, key=tag_key, value=tag_value, type=TagType.CLUSTER
                )
                tag_objs.append(tag)
            cluster.tags.clear()
            cluster.tags.add(*tag_objs)

        cluster_detail = KubernetesApi.cluster_detail({"cluster_id": cluster.id}, use_admin=True)
        namespace = cluster_detail.get("namespace", "")
        params = {
            "bk_username": bk_username,
            "namespace": namespace,
            "clusterName": cluster.name,
            "updatedBy": updated_by or bk_username,
        }
        if cluster_alias is not None:
            params["clusterAlias"] = cluster_alias
        if tags is not None:
            new_tags = [f"{list(t.keys())[0]}:{list(t.values())[0]}" for t in tags]
            params["tags"] = new_tags
        KubernetesApi.update_cluster_meta(params, use_admin=True)
