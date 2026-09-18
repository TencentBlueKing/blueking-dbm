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
from typing import List, Tuple

from django.db.models import QuerySet
from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_meta.enums.spec import SpecMachineType
from backend.db_meta.models import Cluster, Spec
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException


def validate_sqlserver_ha_clusters(cluster_domains: List[str]) -> Tuple[QuerySet, int, int]:
    """校验 SQLServer HA 集群存在且属于同一业务，返回 (cluster_objs, bk_biz_id, bk_cloud_id)。"""
    cluster_objs = Cluster.objects.filter(immute_domain__in=cluster_domains, cluster_type=ClusterType.SqlserverHA)
    if not cluster_objs.exists():
        raise DBMMcpBaseException(msg=_("未找到集群: {}").format(cluster_domains))

    if cluster_objs.count() != len(set(cluster_domains)):
        found_domains = set(cluster_objs.values_list("immute_domain", flat=True))
        missing = set(cluster_domains) - found_domains
        raise DBMMcpBaseException(msg=_("部分集群未找到: {}").format(sorted(missing)))

    bk_biz_ids = list(set(cluster_objs.values_list("bk_biz_id", flat=True)))
    if len(bk_biz_ids) > 1:
        raise DBMMcpBaseException(msg="multi bk biz id found: {}".format(bk_biz_ids))

    bk_cloud_ids = list(set(cluster_objs.values_list("bk_cloud_id", flat=True)))
    if len(bk_cloud_ids) > 1:
        raise DBMMcpBaseException(msg="multi bk cloud id found: {}".format(bk_cloud_ids))

    return cluster_objs, bk_biz_ids[0], bk_cloud_ids[0]


def validate_sqlserver_specs(spec_ids) -> QuerySet:
    """校验目标规格存在且启用，且为 SQLServer 存储规格。"""
    spec_objs = Spec.objects.filter(
        spec_id__in=spec_ids,
        spec_cluster_type=DBType.Sqlserver,
        spec_machine_type=SpecMachineType.SQLSERVER,
        enable=True,
    )
    if spec_objs.count() != len(spec_ids):
        found_ids = set(spec_objs.values_list("spec_id", flat=True))
        missing = spec_ids - found_ids
        raise DBMMcpBaseException(msg=_("目标规格不存在或未启用: spec_id={}").format(sorted(missing)))

    return spec_objs


def check_master_clusters_consistency(input_clusters: QuerySet, ip: str, master_objs: QuerySet):
    """校验 master 实例归属的集群与输入集群完全一致（而非仅数量一致）。"""
    input_cluster_ids = set(input_clusters.values_list("id", flat=True))

    master_cluster_ids = set()
    for master in master_objs:
        master_cluster_ids.update(master.cluster.values_list("id", flat=True))

    if master_cluster_ids != input_cluster_ids:
        raise DBMMcpBaseException(
            msg=_("master ip {ip} 归属集群 {master} 与输入集群 {input} 不一致").format(
                ip=ip,
                master=sorted(master_cluster_ids),
                input=sorted(input_cluster_ids),
            )
        )
