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
from typing import List, NamedTuple, Set

from django.utils.translation import gettext_lazy as _

from backend.components import NameServiceApi
from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.check_response import CheckResponse
from backend.db_report.enums import MetaCheckSubType

_RS_PREVIEW_LIMIT = 8


class ClbEntryCheckSubtypes(NamedTuple):
    meta_incomplete: MetaCheckSubType
    query_failed: MetaCheckSubType
    rs_not_match: MetaCheckSubType


TENDBHA_CLB_SUBTYPES = ClbEntryCheckSubtypes(
    MetaCheckSubType.TenDBHACLBMetaIncomplete,
    MetaCheckSubType.TenDBHACLBQueryFailed,
    MetaCheckSubType.TenDBHACLBRSNotMatchMeta,
)

TENDBCLUSTER_CLB_SUBTYPES = ClbEntryCheckSubtypes(
    MetaCheckSubType.TenDBClusterCLBMetaIncomplete,
    MetaCheckSubType.TenDBClusterCLBQueryFailed,
    MetaCheckSubType.TenDBClusterCLBRSNotMatchMeta,
)


def _is_blank_str(value: str) -> bool:
    return not (value or "").strip()


def _expected_clb_rs_endpoint_set(clb_entry) -> Set[str]:
    """本条 entry 下代理的 ip:port 字符串，格式与名字服务 data.ips 单项一致（DBM 侧按 machine.ip 与 port 拼接）。"""
    endpoints = set()
    for proxy in clb_entry.proxyinstance_set.all():
        endpoints.add("{}:{}".format(proxy.machine.ip, proxy.port))
    return endpoints


def _summarize_rs_targets(targets: Set[str]) -> str:
    if not targets:
        return _("（无）")
    ordered = sorted(targets)
    if len(ordered) <= _RS_PREVIEW_LIMIT:
        return ", ".join(ordered)
    head = ", ".join(ordered[:_RS_PREVIEW_LIMIT])
    return _("{}，等共 {} 个").format(head, len(ordered))


def _clb_meta_missing_fields_msg(cluster_domain: str, entry_label: str, missing_parts: List) -> str:
    return _("CLB 元数据不完整：集群「{}」，CLB 入口「{}」。{}").format(cluster_domain, entry_label, "；".join(missing_parts))


def _clb_query_failure_hint(res) -> str:
    if not isinstance(res, dict):
        return _("返回格式异常，请核对名字服务。")
    raw_hint = res.get("message") or res.get("msg")
    if raw_hint:
        return _("接口说明：{}").format(raw_hint)
    return _("未返回可读说明，请核对名字服务与 CLB 配置。")


def _check_one_clb_entry(ce, cluster_domain: str, subtypes: ClbEntryCheckSubtypes) -> List[CheckResponse]:
    """单条 CLB ClusterEntry：元数据、名字服务查询、RS 与 entry.proxyinstance_set 的 ip:port 一致。"""
    bad = []
    entry_label = ce.entry
    detail = ce.clbentrydetail_set.first()
    if not detail:
        bad.append(
            CheckResponse(
                msg=_("CLB 元数据不完整：集群「{}」的 CLB 入口「{}」缺少详情记录，" "无法核对名字服务中的监听器与后端。").format(cluster_domain, entry_label),
                check_subtype=subtypes.meta_incomplete,
            )
        )
        return bad
    missing_parts = []
    if _is_blank_str(detail.clb_id):
        missing_parts.append(_("负载均衡实例 ID 为空"))
    if _is_blank_str(detail.listener_id):
        missing_parts.append(_("监听器 ID 为空"))
    if _is_blank_str(detail.clb_region):
        missing_parts.append(_("地域为空"))
    if missing_parts:
        bad.append(
            CheckResponse(
                msg=_clb_meta_missing_fields_msg(cluster_domain, entry_label, missing_parts),
                check_subtype=subtypes.meta_incomplete,
            )
        )
        return bad
    try:
        res = NameServiceApi.clb_get_target_private_ips(
            {
                "region": detail.clb_region.strip(),
                "loadbalancerid": detail.clb_id.strip(),
                "listenerid": detail.listener_id.strip(),
            },
            raw=True,
        )
    except Exception as ex:
        bad.append(
            CheckResponse(
                msg=_("无法从名字服务查询该 CLB 的后端列表。集群「{}」，CLB 入口 IP「{}」，地域「{}」，监听器 ID「{}」。" "请求异常：{}").format(
                    cluster_domain, entry_label, detail.clb_region, detail.listener_id, str(ex)
                ),
                check_subtype=subtypes.query_failed,
            )
        )
        return bad
    api_ok = isinstance(res, dict) and res.get("code") == 0
    if not api_ok:
        api_hint = _clb_query_failure_hint(res)
        bad.append(
            CheckResponse(
                msg=_("无法从名字服务查询该 CLB 的后端列表（接口未成功返回）。集群「{}」，CLB 入口 IP「{}」，地域「{}」，" "监听器 ID「{}」。{}").format(
                    cluster_domain, entry_label, detail.clb_region, detail.listener_id, api_hint
                ),
                check_subtype=subtypes.query_failed,
            )
        )
        return bad
    data_block = res.get("data")
    if not isinstance(data_block, dict):
        data_block = {}
    # 接口响应里字段名仍为 ips，元素语义是 CLB 后端 RS，值为 ip:port 字符串列表
    api_rs_items = data_block.get("ips")
    if api_rs_items is None:
        actual_endpoints: Set[str] = set()
    else:
        actual_endpoints = {str(x).strip() for x in api_rs_items if str(x).strip()}
    expected_endpoints = _expected_clb_rs_endpoint_set(ce)
    if expected_endpoints != actual_endpoints:
        only_meta_endpoints = expected_endpoints - actual_endpoints
        only_clb_endpoints = actual_endpoints - expected_endpoints
        bad.append(
            CheckResponse(
                msg=_(
                    "CLB 后端与 DBM 元数据不一致。集群「{}」，CLB 入口「{}」。"
                    "与名字服务 data.ips 返回项（strip 后）及 DBM 拼接的 ip:port 做字符串集合对比。"
                    "仅在 DBM 本条入口登记的 RS（ip:port）：{}。"
                    "仅在 CLB 已绑定、本条入口元数据未登记的 RS（ip:port）：{}。"
                ).format(
                    cluster_domain,
                    entry_label,
                    _summarize_rs_targets(only_meta_endpoints),
                    _summarize_rs_targets(only_clb_endpoints),
                ),
                check_subtype=subtypes.rs_not_match,
            )
        )
    return bad


def collect_clb_entry_check_results(c: Cluster, subtypes: ClbEntryCheckSubtypes) -> List[CheckResponse]:
    """
    遍历集群上所有 CLB ClusterEntry：名字服务可查询、后端 RS 与元数据一致。

    TenDBCluster 若存在 Spider 主/从两套 CLB，则为两条 ClusterEntry；每条仅关联本入口的
    proxyinstance_set（与 CLB 注册 create_by_role 一致），须逐条比对，不可用 cluster.proxyinstance_set
    混算。data.ips 与元数据侧均为 strip 后的字符串集合对比，不做额外改写。
    """
    bad = []
    cluster_domain = c.immute_domain
    for ce in c.clusterentry_set.all():
        if ce.cluster_entry_type != ClusterEntryType.CLB.value:
            continue
        bad.extend(_check_one_clb_entry(ce, cluster_domain, subtypes))
    return bad
