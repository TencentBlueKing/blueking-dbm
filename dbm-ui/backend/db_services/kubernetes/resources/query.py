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
from backend.db_meta.models import AppCache, Cluster
from backend.db_services.dbbase.resources import query
from backend.db_services.dbbase.resources.query import CommonExportQueryResourceMixin, ResourceList
from backend.db_services.kubernetes.utils import offset_to_page
from backend.ticket.constants import TicketType


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
    def _filter_cluster_hook(
        cls,
        bk_biz_id,
        cluster_queryset,
        proxy_queryset,
        storage_queryset,
        limit: int,
        offset: int,
        **kwargs,
    ):
        """
        在父类序列化集群前，批量调用 get_component_spec 构建 cluster_id -> spec 映射并注入 kwargs，
        供 _to_cluster_representation 复用，避免逐集群 N+1 调用。
        """
        bk_username = kwargs.get("bk_username") if kwargs.get("bk_username") else "admin"
        cluster_map = {}
        # 注意：必须迭代 cluster_queryset 的副本(.all())，避免提前评估传入父类的同一 QuerySet 对象，
        # 否则父类 _filter_cluster_hook 中对 cluster_queryset 切片会得到 list 而非 QuerySet，导致 prefetch_related 报错
        for cluster in cluster_queryset.all():
            cluster_detail = KubernetesApi.cluster_detail({"cluster_id": cluster.id}, use_admin=True)
            component_params = {
                "clusterName": cluster.name,
                "k8sClusterName": cluster_detail.get("k8sClusterConfig", {}).get("clusterName", ""),
                "namespace": cluster_detail.get("namespace", ""),
                "bk_username": bk_username,
            }
            cluster_map[cluster.name] = {}
            cluster_map[cluster.name]["detail"] = cluster_detail
            cluster_map[cluster.name]["spec"] = cls.get_component_spec(component_params).get("spec")
        kwargs["cluster_map"] = cluster_map
        return super()._filter_cluster_hook(
            bk_biz_id, cluster_queryset, proxy_queryset, storage_queryset, limit, offset, **kwargs
        )

    @classmethod
    def _to_cluster_representation(
        cls,
        cluster: Cluster,
        cluster_entry: List[Dict[str, str]],
        db_module_names_map: Dict[int, str],
        cluster_entry_map: Dict[int, Dict[str, str]],
        cluster_operate_records_map: Dict[int, List],
        cloud_info: Dict[str, Any],
        biz_info: AppCache,
        cluster_stats_map: Dict[str, Dict[str, int]],
        cluster_zone_map: Dict[str, str],
        dns_to_clb: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """将集群对象转为可序列化的 dict 结构"""

        cluster_map = kwargs.get("cluster_map", {})
        cluster_info_map = cluster_map.get(cluster.name) or {}
        cluster_detail = cluster_info_map.get("detail") or KubernetesApi.cluster_detail(
            {"cluster_id": cluster.id}, use_admin=True
        )
        k8s_cluster_name = cluster_detail.get("k8sClusterConfig", {}).get("clusterName", "")
        namespace = cluster_detail.get("namespace", "")
        components = cluster_detail.get("addonInfo", {}).get("topology", {}).get("components", [])
        # 复用外层批量构建的 cluster_name -> cluster_spec 映射，避免逐集群重复调用
        cluster_spec = cluster_info_map.get("spec")

        cluster_extra_info = {
            "k8s_cluster_name": k8s_cluster_name,
            "namespace": namespace,
            "components": components,
            "major_version": cluster_detail.get("serviceVersion", ""),
            "cluster_spec": cluster_spec,
        }
        cluster_info = super()._to_cluster_representation(
            cluster,
            cluster_entry,
            db_module_names_map,
            cluster_entry_map,
            cluster_operate_records_map,
            cloud_info,
            biz_info,
            cluster_stats_map,
            cluster_zone_map,
            dns_to_clb,
            **kwargs,
        )
        cluster_info.update(cluster_extra_info)
        return cluster_info

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
        result = {"count": 0, "data": []}

        # 支持多集群查询：解析集群参数，只支持逗号分隔的字符串格式
        cluster_names = query_params.get("cluster_name", "")
        k8s_cluster_names = query_params.get("k8s_cluster_name", "")
        namespaces = query_params.get("namespace", "")

        # 解析多值参数（逗号分隔的字符串）
        cluster_name_list = cluster_names.split(",") if cluster_names else []
        k8s_cluster_name_list = k8s_cluster_names.split(",") if k8s_cluster_names else []
        namespace_list = namespaces.split(",") if namespaces else []

        if len(cluster_name_list) != len(k8s_cluster_name_list) or len(cluster_name_list) != len(namespace_list):
            raise ValueError(_("cluster_name, k8s_cluster_name, namespace 参数数量必须一致"))

        # 批量反查 cluster_id，用于权限字段嵌入(viewsets.list_instances 的 id_field=lambda d: d["cluster_id"])
        # 构建 cluster_name -> cluster_id 的映射
        cluster_id_map = {}
        cluster_ids = query_params.get("cluster_id")
        if cluster_ids:
            # 如果传入了 cluster_id，支持多选（只支持逗号分隔的字符串格式）
            id_list = cluster_ids.split(",") if cluster_ids else []
            clusters = Cluster.objects.filter(bk_biz_id=bk_biz_id, id__in=id_list).only("id", "name")
            cluster_id_map = {c.name: c.id for c in clusters}
        else:
            # 通过集群名反查，支持多选
            if cluster_name_list:
                clusters = Cluster.objects.filter(bk_biz_id=bk_biz_id, name__in=cluster_name_list).only("id", "name")
                cluster_id_map = {c.name: c.id for c in clusters}

        # 构建查询集群列表：如果有多集群，循环查询；否则按原逻辑查询
        # 如果未配置 instance_roles，则按一次不带 componentName 的请求处理
        roles = cls.instance_roles or [None]

        # 确定需要查询的集群列表
        if not cluster_name_list:
            # 没有指定集群，不查询
            return ResourceList(**result)

        for idx, cluster_name in enumerate(cluster_name_list):
            # 获取当前集群对应的 k8s_cluster_name 和 namespace（如果有多值则按索引对应，否则共用）
            k8s_cluster_name = (
                k8s_cluster_name_list[idx]
                if idx < len(k8s_cluster_name_list)
                else (k8s_cluster_name_list[0] if k8s_cluster_name_list else "")
            )
            namespace = (
                namespace_list[idx] if idx < len(namespace_list) else (namespace_list[0] if namespace_list else "")
            )

            data = {
                "k8sClusterName": k8s_cluster_name,
                "clusterName": cluster_name,
                "namespace": namespace,
            }

            # 获取当前集群的 cluster_id
            current_cluster_id = cluster_id_map.get(cluster_name)

            for role in roles:
                if role is not None:
                    data["componentName"] = role
                res = KubernetesApi.component_pods(data, use_admin=True) or {}
                result["count"] += res.get("count", 0)
                pods = res.get("result") or []
                # 给每条 pod 数据补充 cluster_id，供权限装饰器(id_field=lambda d: d["cluster_id"])使用
                # 每个 pod 关联它所属的集群 ID
                for pod in pods:
                    pod["cluster_id"] = current_cluster_id
                result["data"].extend(pods)

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
