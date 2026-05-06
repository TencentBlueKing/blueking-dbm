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
import copy
import logging
import time
from datetime import datetime, timedelta, timezone

from backend import env
from backend.components import BKMonitorV3Api
from backend.db_meta.enums import ClusterType, InstanceStatus, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_monitor.constants import EXPORTER_UP_QUERY_TEMPLATE
from backend.db_periodic_task.local_tasks.db_meta.constants import UNIFY_QUERY_PARAMS
from backend.db_report.enums import ReportStateType
from backend.db_report.enums.mysql_exporter_check_sub_type import MysqlExporterCheckSubType
from backend.db_report.models.mysql_exporter_check_report import MysqlExporterCheckReport

logger = logging.getLogger("root")


def get_exporter_failed_duration(cluster_domain: str, instance: str, check_time: datetime):
    """
    获取 exporter 检查失败的持续天数
    参数:
        cluster_domain: 集群域名
        instance: 实例地址
        subtype: 检查子类型
        check_time: 当前检查时间
    返回:
        失败持续天数
    """
    # 查找最近一次成功的记录
    last_failed = (
        MysqlExporterCheckReport.objects.filter(
            cluster=cluster_domain,
            instance=instance,
            state=ReportStateType.ABNORMAL.value,
            create_at__lt=check_time,
            create_at__gt=check_time - timedelta(days=1),
        )
        .order_by("-create_at")
        .first()
    )

    # 如果没有找到成功记录，统计所有失败记录数
    if last_failed:
        return last_failed.failed_days + 1
    else:
        return 1


def query_cluster_exporter_up(db_type, exporter):
    """查询某类集群的 exporter 是否正常"""
    # 获取查询模板
    query_template = EXPORTER_UP_QUERY_TEMPLATE.get(db_type)
    if not query_template:
        logger.error("No query template for cluster type: %s and exporter: %s", db_type, exporter)
        return {}

    # 查询业务固定为DBA，查询时间取模板range
    params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    params["end_time"] = int(time.time())
    params["start_time"] = params["end_time"] - int(query_template["range"]) * 60
    params["query_configs"][0]["promql"] = query_template[exporter]

    # 查询exporter up指标
    series = BKMonitorV3Api.unify_query(params)["series"]
    cluster_exporter_up_map = {}
    for data in series:
        if data["datapoints"]:
            dim = data["dimensions"]
            unique_key = "{}#{}#{}".format(dim["appid"], dim["cluster_domain"], dim["instance"])
            cluster_exporter_up_map[unique_key] = dim["instance_role"]
    # map is like: {'appid#cluster_domain#host-port': 'instance_role', '1#xxx#yyy-3306': 'remote_slave'}
    return cluster_exporter_up_map


def report_to_db(c: Cluster, exporter_map: dict, instance, instance_role):
    """
    将查询结果写入数据库
    instance_role 是实例的角色，不同实例类型的角色查询方法不一样，这里从外面传入
    """
    # 构造唯一键：appid#cluster_domain#host-port
    subtype = ""
    if isinstance(instance, StorageInstance):
        subtype = MysqlExporterCheckSubType.MysqldExporterUp
        # instance = StorageInstance(instance)
    elif c.cluster_type == ClusterType.TenDBCluster:
        subtype = MysqlExporterCheckSubType.MysqldExporterUp
    else:
        subtype = MysqlExporterCheckSubType.MysqlproxyExporterUp

    unique_key = "{}#{}#{}".format(instance.bk_biz_id, c.immute_domain, f"{instance.machine.ip}-{instance.port}")
    msg = ""
    if unique_key not in exporter_map:
        msg = f"Instance {instance.ip_port} ({instance_role}) not reporting metric"
        logger.warning(f"{c.immute_domain}: {msg}")
    elif instance_role != exporter_map[unique_key]:
        msg = (
            f"Instance {instance.ip_port} ({instance_role}) "
            f"reporting wrong instance_role: {exporter_map[unique_key]}"
        )
        logger.warning(f"{c.immute_domain}: {msg}")
    if msg:
        check_time = datetime.now(timezone.utc)
        failed_days = get_exporter_failed_duration(c.immute_domain, instance.ip_port, check_time)
        MysqlExporterCheckReport.objects.create(
            bk_biz_id=c.bk_biz_id,
            bk_cloud_id=c.bk_cloud_id,
            cluster=c.immute_domain,
            cluster_type=c.cluster_type,
            instance=instance.ip_port,
            status=False,
            msg=msg,
            subtype=subtype,
            state=ReportStateType.ABNORMAL.value,
            failed_days=failed_days,
        )


def check_tendbha_exporter_up():
    """
    检查 集群里的每个实例 是否有上报 mysql_up 指标，且上报的 instance_role 是正确的
    query_cluster_exporter_up
    """
    logger.info("tendbha_exporter_up checking")
    # tendbha backend use mysql_up
    tendbha_exporter_up_map = query_cluster_exporter_up(ClusterType.TenDBHA, "dbm_mysqld_exporter")
    if len(tendbha_exporter_up_map) <= 2:
        # 大概率查询异常，忽略
        logger.warning("tendbha_exporter_up return less than 2 results: %s", tendbha_exporter_up_map)
        return

    # 检查 TenDBHA 集群的 StorageInstance
    for c in Cluster.objects.filter(cluster_type=ClusterType.TenDBHA).prefetch_related(
        "storageinstance_set", "storageinstance_set__machine"
    ):
        for storage in c.storageinstance_set.filter(status=InstanceStatus.RUNNING):
            # 构造唯一键：appid#cluster_domain#host-port#instance_role
            report_to_db(c, tendbha_exporter_up_map, storage, storage.instance_role)

    # tendbha proxy use mysqlproxy_up
    proxy_exporter_up_map = query_cluster_exporter_up(ClusterType.TenDBHA, "dbm_mysqlproxy_exporter")
    if len(proxy_exporter_up_map) <= 2:
        # 大概率查询异常，忽略
        logger.warning("proxy_exporter_up return less than 2 results: %s", proxy_exporter_up_map)
        return

    for c in Cluster.objects.filter(cluster_type=ClusterType.TenDBHA).prefetch_related(
        "proxyinstance_set", "proxyinstance_set__machine"
    ):
        # 关联 ProxyInstance 表，拿到 bk_biz_id,cluster_domain,host-port,instance_role
        # 然后根据 query_cluster_exporter_up 的查询结果判断 是否上报 mysqlproxy_up 指标
        for proxy in c.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
            instance_role = "proxy"
            report_to_db(c, proxy_exporter_up_map, proxy, instance_role)


def check_tendbcluster_exporter_up():
    logger.info("tendbcluster_exporter_up checking")
    # tendbcluster backend and proxy both use mysql_up
    tendbcluster_exporter_up_map = query_cluster_exporter_up(ClusterType.TenDBCluster, "dbm_mysqld_exporter")
    if len(tendbcluster_exporter_up_map) <= 2:
        # 大概率查询异常，忽略
        logger.warning("tendbcluster_exporter_up return less than 2 results: %s", tendbcluster_exporter_up_map)
        return

    # 检查 TenDBCluster 集群的 StorageInstance 和 ProxyInstance
    for c in Cluster.objects.filter(cluster_type=ClusterType.TenDBCluster).prefetch_related(
        "storageinstance_set", "storageinstance_set__machine", "proxyinstance_set", "proxyinstance_set__machine"
    ):
        # 检查 StorageInstance
        for storage in c.storageinstance_set.filter(status=InstanceStatus.RUNNING):
            report_to_db(c, tendbcluster_exporter_up_map, storage, storage.instance_role)

        # 检查 ProxyInstance (TenDBCluster 的 spider 节点也上报 mysql_up)
        for proxy in c.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
            # TenDBCluster 的 proxy 是 spider 节点，需要获取 spider_role
            spider_role = ""
            if hasattr(proxy, "tendbclusterspiderext"):
                spider_role = proxy.tendbclusterspiderext.spider_role
            if (
                spider_role == TenDBClusterSpiderRole.SPIDER_MNT
                or spider_role == TenDBClusterSpiderRole.SPIDER_SLAVE_MNT
            ):
                continue
            report_to_db(c, tendbcluster_exporter_up_map, proxy, spider_role)


def check_tendbsingle_exporter_up():
    logger.info("tendbsingle_exporter_up checking")
    # tendbsingle use mysql_up
    tendbsingle_exporter_up_map = query_cluster_exporter_up(ClusterType.TenDBSingle, "dbm_mysqld_exporter")
    if len(tendbsingle_exporter_up_map) <= 2:
        # 大概率查询异常，忽略
        logger.warning("tendbsingle_exporter_up return less than 2 results: %s", tendbsingle_exporter_up_map)
        return

    # 检查 TenDBSingle 集群的 StorageInstance
    for c in Cluster.objects.filter(cluster_type=ClusterType.TenDBSingle).prefetch_related(
        "storageinstance_set", "storageinstance_set__machine"
    ):
        # 关联 StorageInstance 表，拿到 bk_biz_id,cluster_domain,host-port,instance_role
        # 然后根据 query_cluster_exporter_up 的查询结果判断 是否上报 mysql_up 指标
        for storage in c.storageinstance_set.filter(status=InstanceStatus.RUNNING):
            report_to_db(c, tendbsingle_exporter_up_map, storage, storage.instance_role)
