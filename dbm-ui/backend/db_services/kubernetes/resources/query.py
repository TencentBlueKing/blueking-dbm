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


class KubernetesBaseExportQueryResourceMixin(CommonExportQueryResourceMixin):
    """补充k8s集群列表导出所需的header及数据父类"""

    @classmethod
    def update_headers(cls, headers, **kwargs):
        """
        更新的headers列表数据
        """
        filtered_headers = list(filter(lambda header: header["id"] not in ["slave_domain", "db_module_name"], headers))
        return filtered_headers, kwargs["extra_headers"]

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

        cluster_detail = KubernetesApi.cluster_detail({"cluster_id": cluster.id}, use_admin=True)
        k8s_cluster_name = cluster_detail.get("k8sClusterConfig", {}).get("clusterName", "")
        namespace = cluster_detail.get("namespace", "")

        cluster_extra_info = {
            "k8s_cluster_name": k8s_cluster_name,
            "namespace": namespace,
            "components": cluster_detail.get("addonInfo", {}).get("topology", {}).get("components", []),
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
        data = {
            "k8sClusterName": query_params["k8s_cluster_name"],
            "clusterName": query_params["cluster_name"],
            "namespace": query_params["namespace"],
            # "componentName": query_params["role"],
        }
        for role in cls.instance_roles:
            data["componentName"] = role

        res = KubernetesApi.component_pods(data, use_admin=True)
        result["count"] += res.get("count", 0)
        result["data"].extend(res.get("data", []))
        return ResourceList(**result)

    @classmethod
    def retrieve_ins(cls, query_params) -> dict:
        res = KubernetesApi.pod_detail(query_params, use_admin=True)
        return res

    @classmethod
    def get_operation_log(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> ResourceList:
        """查询集群列表，补充公共字段"""
        query_params = offset_to_page(query_params)
        res = KubernetesApi.cluster_operation_log(query_params, use_admin=True)
        return ResourceList(**res)

    @classmethod
    def get_component_spec(cls, query_params):
        res = KubernetesApi.cluster_describe(query_params, use_admin=True)
        return res
