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

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.mysql.dts.precheck.mysql_dts_precheck_subflow import mysql_dts_precheck_subflow
from backend.flow.plugins.components.collections.mysql.dts.precheck.topology_check import (
    MysqlDtsPrecheckTopologyComponent,
)
from backend.flow.utils.mysql.dts.constants import MigrateTopology
from backend.flow.utils.mysql.dts.precheck.collector import PrecheckCollectError
from backend.flow.utils.mysql.dts.precheck.migrate_input import expand_precheck_pairs
from backend.flow.utils.mysql.dts.precheck.topology import ROUTE_COVERAGE_ITEM, SOURCE_LANDING_ITEM

SUPPORTED_CLUSTER_TYPES = {
    ClusterType.TenDBHA.value,
    ClusterType.TenDBSingle.value,
    ClusterType.TenDBCluster.value,
}


class MysqlDtsPrecheckFlow:
    def __init__(self, root_id: str, data: dict):
        self.root_id = root_id
        self.data = data

    def resolve_pairs(self) -> list[dict]:
        """按 migrate 展开源/目标，并用集群 ID 补上域名。"""
        if not self.data.get("bk_biz_id"):
            raise PrecheckCollectError(_("缺少 bk_biz_id，无法解析预检查集群"))
        try:
            pairs = expand_precheck_pairs(self.data)
        except ValueError as exc:
            raise PrecheckCollectError(str(exc)) from exc

        cluster_ids = {pair["source_cluster_id"] for pair in pairs} | {pair["target_cluster_id"] for pair in pairs}
        clusters = {
            cluster.id: cluster
            for cluster in Cluster.objects.filter(bk_biz_id=self.data["bk_biz_id"], id__in=cluster_ids)
        }
        for pair in pairs:
            for role, cluster_id in (
                ("source", pair["source_cluster_id"]),
                ("target", pair["target_cluster_id"]),
            ):
                cluster = clusters.get(cluster_id)
                if cluster is None:
                    raise PrecheckCollectError(_("业务 {} 下不存在集群 {}").format(self.data["bk_biz_id"], cluster_id))
                if cluster.cluster_type not in SUPPORTED_CLUSTER_TYPES:
                    raise PrecheckCollectError(_("集群 {} 类型 {} 不支持 DTS 预检查").format(cluster_id, cluster.cluster_type))
                pair[f"{role}_cluster_domain"] = cluster.immute_domain
        self.data["pairs"] = pairs
        return pairs

    def run_flow(self):
        self.data.setdefault("uid", self.root_id)
        pairs = self.resolve_pairs()
        pipeline = Builder(root_id=self.root_id, data=self.data)
        enabled_codes = self.data.get("enabled_codes")
        branches = []
        for pair in pairs:
            subflow = mysql_dts_precheck_subflow(
                root_id=self.root_id,
                data={**self.data, **pair, "enabled_codes": enabled_codes},
                enabled_codes=enabled_codes,
            )
            branches.append(
                subflow.build_sub_process(
                    sub_name=_("MySQL DTS 迁移预检查 {} -> {}").format(
                        pair["source_cluster_domain"], pair["target_cluster_domain"]
                    )
                )
            )
        for topology, group in _topology_groups(pairs):
            item = SOURCE_LANDING_ITEM if topology == MigrateTopology.MANY_TO_ONE.value else ROUTE_COVERAGE_ITEM
            topo = SubBuilder(root_id=self.root_id, data=self.data)
            topo.add_act(
                act_name=item.name,
                act_component_code=MysqlDtsPrecheckTopologyComponent.code,
                kwargs={
                    "bk_biz_id": self.data.get("bk_biz_id"),
                    "enabled_codes": enabled_codes,
                    "topology": topology,
                    "pairs": group,
                },
            )
            branches.append(topo.build_sub_process(sub_name=item.name))
        if len(branches) == 1:
            pipeline.add_sub_pipeline(branches[0])
        else:
            pipeline.add_parallel_sub_pipeline(branches)
        pipeline.run_pipeline()


def _topology_groups(pairs: list[dict]) -> list[tuple[str, list[dict]]]:
    grouped: dict[tuple[int, str], list[dict]] = {}
    order: list[tuple[int, str]] = []
    for pair in pairs:
        if pair["topology"] not in (MigrateTopology.MANY_TO_ONE.value, MigrateTopology.ONE_TO_MANY.value):
            continue
        key = (pair["infos_index"], pair["topology"])
        if key not in grouped:
            order.append(key)
            grouped[key] = []
        grouped[key].append(pair)
    return [(topology, grouped[(infos_index, topology)]) for infos_index, topology in order]
