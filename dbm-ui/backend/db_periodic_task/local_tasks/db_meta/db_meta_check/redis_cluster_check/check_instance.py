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
from collections import defaultdict
from typing import Dict, List, Optional, Set, Union

from django.db.models import Prefetch, Q
from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterPhase, ClusterType, InstanceRole, InstanceStatus
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.db_meta.models.storage_instance_tuple import StorageInstanceTuple
from backend.db_report.enums import MetaCheckSubType, ReportStateType
from backend.db_report.portrait.redis_dimensions import RedisPortraitDimensionCode
from backend.db_report.portrait.redis_ingest import ingest_abnormal_cluster_rows
from backend.flow.utils.redis.redis_report_utils import (
    META_CHECK_CLUSTER_PAGE_SIZE,
    RedisReportWriter,
    _chunked,
    delete_old_meta_check_reports,
    is_cluster_labeled_with,
    safe_write_meta_reports,
)
from backend.ticket.constants import TICKET_RUNNING_STATUS_SET, TicketType
from backend.ticket.models.ticket import ClusterOperateRecord

logger = logging.getLogger("root")

IGNORE_TICKET_TYPES = [
    TicketType.REDIS_INSTANCE_CLOSE.value,
    TicketType.REDIS_PROXY_CLOSE.value,
    TicketType.REDIS_DESTROY.value,
    TicketType.REDIS_INSTANCE_DESTROY.value,
]


def _storage_prefetch_qs():
    return StorageInstance.objects.select_related("machine").prefetch_related(
        Prefetch("as_ejector", queryset=StorageInstanceTuple.objects.select_related("receiver__machine")),
        Prefetch("as_receiver", queryset=StorageInstanceTuple.objects.select_related("ejector__machine")),
    )


def get_supported_clusters():
    return [
        ClusterType.TendisTwemproxyRedisInstance.value,
        ClusterType.TwemproxyTendisSSDInstance.value,
        ClusterType.TendisPredixyRedisCluster.value,
        ClusterType.TendisPredixyTendisplusCluster.value,
        ClusterType.TendisRedisInstance.value,
    ]


def _load_clusters_page(cluster_ids: List[int]):
    if not cluster_ids:
        return []
    return list(
        Cluster.objects.filter(id__in=cluster_ids).prefetch_related(
            Prefetch("proxyinstance_set", queryset=ProxyInstance.objects.select_related("machine")),
            Prefetch("storageinstance_set", queryset=_storage_prefetch_qs()),
            "tags",
        )
    )


def _fetch_ignore_cluster_ids(cluster_ids: List[int]) -> Set[int]:
    if not cluster_ids:
        return set()
    return set(
        ClusterOperateRecord.objects.filter(
            ticket__ticket_type__in=IGNORE_TICKET_TYPES,
            ticket__status__in=TICKET_RUNNING_STATUS_SET,
            cluster_id__in=cluster_ids,
        ).values_list("cluster_id", flat=True)
    )


def _resolve_creator(dba_cache: Dict[int, str], bk_biz_id: int) -> str:
    if bk_biz_id not in dba_cache:
        dba_list = DBAdministrator.get_biz_db_type_admins(bk_biz_id=bk_biz_id, db_type=DBType.Redis.value)
        dba_cache[bk_biz_id] = dba_list[0] if dba_list else "admin"
    return dba_cache[bk_biz_id]


def _should_ignore_cluster(cluster: Cluster, ignore_cluster_ids: Set[int]) -> bool:
    if cluster.phase != ClusterPhase.ONLINE.value:
        logger.info(
            "instance_check: will ignore cluster %s, cluster phase is %s (not online)",
            cluster,
            cluster.phase,
        )
        return True
    if cluster.id in ignore_cluster_ids:
        logger.info("instance_check: will ignore cluster %s , 4 it has destory label", cluster)
        return True
    return False


def check_redis_instance():
    cluster_types = get_supported_clusters()
    writer = RedisReportWriter()
    dba_cache: Dict[int, str] = {}

    delete_old_meta_check_reports(
        MetaCheckSubType.AloneInstance, cluster_types=cluster_types, days=writer.retention_days
    )
    delete_old_meta_check_reports(
        MetaCheckSubType.StatusAbnormal, cluster_types=cluster_types, days=writer.retention_days
    )

    query = Q(cluster_type__in=cluster_types)
    all_cluster_ids = list(Cluster.objects.filter(query).values_list("id", flat=True))
    ignore_cluster_ids = _fetch_ignore_cluster_ids(all_cluster_ids)

    for page_ids in _chunked(all_cluster_ids, META_CHECK_CLUSTER_PAGE_SIZE):
        page_rows: List[dict] = []
        for cluster in _load_clusters_page(page_ids):
            logger.info("instance_check: start by %s", cluster)
            if _should_ignore_cluster(cluster, ignore_cluster_ids):
                continue

            creator = _resolve_creator(dba_cache, cluster.bk_biz_id)
            page_rows.extend(_check_single_cluster_instance(cluster, creator))

        if page_rows:
            safe_write_meta_reports(writer, page_rows, context="instance_check page")
            ingest_abnormal_cluster_rows(
                page_rows,
                dimension=RedisPortraitDimensionCode.TOPOLOGY_SCALE,
                prefix_by_subtype={
                    MetaCheckSubType.AloneInstance.value: "[孤立实例]",
                    MetaCheckSubType.StatusAbnormal.value: "[实例状态]",
                },
            )


def _check_single_cluster_instance(cluster: Cluster, creator: str) -> List[dict]:
    report_rows: List[dict] = []
    cluster_has_lonely_issue = False

    skip_proxy_count_check = cluster.cluster_type == ClusterType.TendisRedisInstance.value or is_cluster_labeled_with(
        cluster,
        {"directmode": "true"},
    )
    proxy_instances = list(cluster.proxyinstance_set.all())
    if not skip_proxy_count_check and len(proxy_instances) < 2:
        cluster_has_lonely_issue = True
        msg = _("cluster:{} now had proxies[{}] < 2").format(cluster.immute_domain, len(proxy_instances))
        report_rows.append(
            _alone_instance_row(cluster, ip="none", port=None, msg=msg, creator=creator, machine_type="")
        )
    else:
        logger.info(
            "cluster:%s proxy count check passed, proxies count: %s",
            cluster.immute_domain,
            len(proxy_instances),
        )

    master_slave_map, slave_master_map = defaultdict(list), defaultdict()
    storage_instances = list(cluster.storageinstance_set.all())
    for master_obj in storage_instances:
        if master_obj.instance_role != InstanceRole.REDIS_MASTER.value:
            continue
        try:
            slave_tuples = list(master_obj.as_ejector.all())
            if not slave_tuples:
                cluster_has_lonely_issue = True
                logger.warning(
                    "Warning: cluster %s master %s has no slave configured", cluster.immute_domain, master_obj
                )
                msg = _("集群{}的master：{} 获取slave失败").format(cluster.immute_domain, master_obj)
                report_rows.append(_alone_instance_row(cluster, master_obj, msg, creator))
                continue

            slave_objs = [tuple_obj.receiver for tuple_obj in slave_tuples]
            all_slaves_valid = True
            for slave_obj in slave_objs:
                master_slave_map[master_obj.machine.ip].append(slave_obj.machine.ip)
                if master_obj.port != slave_obj.port:
                    cluster_has_lonely_issue = True
                    all_slaves_valid = False
                    msg = _("集群{}的master实例：{} 的slave {} 端口不匹配").format(cluster.immute_domain, master_obj, slave_obj)
                    report_rows.append(_alone_instance_row(cluster, master_obj, msg, creator))

            if all_slaves_valid:
                slave_ips = ", ".join(slave.machine.ip for slave in slave_objs)
                logger.info(
                    _("集群{}的master实例：{} slave关系正常，共{}个slave: {}").format(
                        cluster.immute_domain, master_obj, len(slave_objs), slave_ips
                    )
                )
        except Exception as e:
            cluster_has_lonely_issue = True
            logger.warning(
                "Warning: unexpected error while checking master %s in cluster %s: %s",
                master_obj,
                cluster.immute_domain,
                e,
            )
            msg = _("集群{}的master实例：{} 检查时发生异常: {}").format(cluster.immute_domain, master_obj, e)
            report_rows.append(_alone_instance_row(cluster, master_obj, msg, creator))

    for slave_obj in storage_instances:
        if slave_obj.instance_role != InstanceRole.REDIS_SLAVE.value:
            continue
        try:
            receiver_tuples = list(slave_obj.as_receiver.all())
            if not receiver_tuples:
                cluster_has_lonely_issue = True
                logger.warning(
                    "Warning: cluster %s slave %s failed to get master_obj",
                    cluster.immute_domain,
                    slave_obj,
                )
                msg = _("集群{}的slave：{} 获取master失败").format(cluster.immute_domain, slave_obj)
                report_rows.append(_alone_instance_row(cluster, slave_obj, msg, creator))
                continue
            master_obj = receiver_tuples[0].ejector

            ifmaster = slave_master_map.get(slave_obj.machine.ip)
            if ifmaster and ifmaster != master_obj.machine.ip:
                cluster_has_lonely_issue = True
                logger.warning(
                    "Warning: cluster %s unsupport multiple masters for slave %s",
                    cluster.immute_domain,
                    slave_obj.machine.ip,
                )
                msg = _("unsupport mutil master with cluster {} 4:{}").format(
                    cluster.immute_domain, slave_obj.machine.ip
                )
                report_rows.append(_alone_instance_row(cluster, slave_obj, msg, creator))
                continue

            slave_master_map[slave_obj.machine.ip] = master_obj.machine.ip
            if slave_obj.port != master_obj.port:
                cluster_has_lonely_issue = True
                msg = _("集群{}的slave实例：{} 没有master").format(cluster.immute_domain, slave_obj)
                report_rows.append(_alone_instance_row(cluster, slave_obj, msg, creator))
            else:
                logger.info(_("集群{}的slave实例：{} master关系正常").format(cluster.immute_domain, slave_obj))
        except Exception as e:
            cluster_has_lonely_issue = True
            logger.warning(
                "Warning: unexpected error while checking slave %s in cluster %s: %s",
                slave_obj,
                cluster.immute_domain,
                e,
            )
            msg = _("集群{}的slave实例：{} 检查时发生异常: {}").format(cluster.immute_domain, slave_obj, e)
            report_rows.append(_alone_instance_row(cluster, slave_obj, msg, creator))

    status_rows, cluster_has_status_issue = _collect_status_abnormal_rows(
        cluster, creator, instance_objs=storage_instances + proxy_instances
    )
    report_rows.extend(status_rows)

    if not cluster_has_lonely_issue:
        report_rows.append(_cluster_normal_row(cluster, MetaCheckSubType.AloneInstance, creator))
    if not cluster_has_status_issue:
        report_rows.append(_cluster_normal_row(cluster, MetaCheckSubType.StatusAbnormal, creator))

    return report_rows


def _collect_status_abnormal_rows(
    cluster: Cluster,
    creator: str,
    instance_objs: Optional[List[Union[StorageInstance, ProxyInstance]]] = None,
) -> tuple[List[dict], bool]:
    cluster_has_status_issue = False
    rows: List[dict] = []

    if instance_objs is None:
        instance_objs = list(cluster.storageinstance_set.all()) + list(cluster.proxyinstance_set.all())

    for instance_obj in instance_objs:
        try:
            if instance_obj.status != InstanceStatus.RUNNING:
                cluster_has_status_issue = True
                msg = _("集群{}的实例:{}实例状态异常:{}").format(cluster.immute_domain, instance_obj.ip_port, instance_obj.status)
                rows.append(
                    {
                        "cluster": cluster,
                        "ip": instance_obj.machine.ip,
                        "port": instance_obj.port,
                        "subtype": MetaCheckSubType.StatusAbnormal,
                        "msg": msg,
                        "state": ReportStateType.ABNORMAL,
                        "machine_type": instance_obj.machine_type,
                        "creator": creator,
                    }
                )
        except Exception as e:
            cluster_has_status_issue = True
            logger.warning(
                "Warning: unexpected error while checking instance %s in cluster %s: %s",
                instance_obj,
                cluster.immute_domain,
                e,
            )

    return rows, cluster_has_status_issue


def _alone_instance_row(cluster, instance_obj=None, msg="", creator="admin", ip=None, port=None, machine_type=""):
    if instance_obj is not None:
        ip = instance_obj.machine.ip
        port = instance_obj.port
        machine_type = instance_obj.machine_type
    return {
        "cluster": cluster,
        "ip": ip,
        "port": port,
        "subtype": MetaCheckSubType.AloneInstance,
        "msg": msg,
        "state": ReportStateType.ABNORMAL,
        "machine_type": machine_type,
        "creator": creator,
    }


def _cluster_normal_row(cluster, subtype, creator="admin"):
    msg = _("集群{}所有实例检查通过").format(cluster.immute_domain)
    logger.info("instance_check: cluster %s passed", cluster.immute_domain)
    return {
        "cluster": cluster,
        "ip": "all",
        "port": None,
        "subtype": subtype,
        "msg": msg,
        "state": ReportStateType.NORMAL,
        "creator": creator,
    }


# Backward-compatible helpers for external callers/tests.
def check_cluster_instance_status(cluster: Cluster, creator: str = "admin", writer: RedisReportWriter = None) -> bool:
    rows, has_issue = _collect_status_abnormal_rows(cluster, creator)
    if writer and rows:
        writer.write_meta_reports(rows)
    return has_issue


def check_ignore(cluster) -> bool:
    return _should_ignore_cluster(cluster, _fetch_ignore_cluster_ids([cluster.id]))


def check_status_create_abnormal(c, instance_obj, creator="admin", writer: RedisReportWriter = None):
    if instance_obj.status != InstanceStatus.RUNNING:
        row = {
            "cluster": c,
            "ip": instance_obj.machine.ip,
            "port": instance_obj.port,
            "subtype": MetaCheckSubType.StatusAbnormal,
            "msg": _("集群{}的实例:{}实例状态异常:{}").format(c.immute_domain, instance_obj.ip_port, instance_obj.status),
            "state": ReportStateType.ABNORMAL,
            "machine_type": instance_obj.machine_type,
            "creator": creator,
        }
        if writer:
            writer.write_meta_reports([row])
        else:
            RedisReportWriter().write_meta_reports([row])
        return False
    return True


def create_single_node_record(c, instance_obj, msg, creator="admin", writer: RedisReportWriter = None):
    row = _alone_instance_row(c, instance_obj, msg, creator)
    if writer:
        writer.write_meta_reports([row])
    else:
        RedisReportWriter().write_meta_reports([row])


def create_cluster_normal_report(c, report_type, creator="admin", writer: RedisReportWriter = None):
    row = _cluster_normal_row(c, report_type, creator)
    if writer:
        writer.write_meta_reports([row])
    else:
        RedisReportWriter().write_meta_reports([row])
