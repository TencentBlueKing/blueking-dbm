import copy
import logging
import time

from backend import env
from backend.components import BKMonitorV3Api
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.db_meta.constants import EXPORTER_UP_QUERY_TEMPLATE, UNIFY_QUERY_PARAMS

logger = logging.getLogger("celery")


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
    cluster_exporter_up_stats = []
    for data in series:
        if data["datapoints"]:
            dim = data["dimensions"]
            unique_key = "{}#{}#{}#{}".format(
                dim["appid"], dim["cluster_domain"], dim["instance"], dim["instance_role"]
            )
            cluster_exporter_up_map[unique_key] = len(data["datapoints"])
            one_stat = dict(dim)
            one_stat["up_count"] = len(data["datapoints"])
            cluster_exporter_up_stats.append(one_stat)
    # map is like: {'appid#cluster_domain#host-port#instance_role': 1, '1#xxx#yyy-3306#zzz': 2}
    return cluster_exporter_up_map


def check_tendbha_exporter_up():
    """
    检查 集群里的每个实例 是否有上报 mysql_up 指标，且上报的 instance_role 是正确的
    query_cluster_exporter_up
    """
    # tendbha backend use mysql_up
    tendbha_exporter_up_map = query_cluster_exporter_up(ClusterType.TenDBHA, "dbm_mysqld_exporter")
    if len(tendbha_exporter_up_map) <= 2:
        # 大概率查询异常，忽略
        logger.warning("tendbha_exporter_up_map return less than 2 results: %s", tendbha_exporter_up_map)
        return

    # 检查 TenDBHA 集群的 StorageInstance
    for c in Cluster.objects.filter(cluster_type=ClusterType.TenDBHA).prefetch_related(
        "storageinstance_set", "storageinstance_set__machine"
    ):
        for storage in c.storageinstance_set.filter(status=InstanceStatus.RUNNING):
            # 构造唯一键：appid#cluster_domain#host-port#instance_role
            unique_key = "{}#{}#{}#{}".format(
                storage.bk_biz_id, c.immute_domain, f"{storage.machine.ip}-{storage.port}", storage.instance_role
            )

            # 检查是否在查询结果中
            if unique_key not in tendbha_exporter_up_map:
                logger.warning(
                    "StorageInstance %s (cluster: %s, role: %s) not reporting mysql_up metric",
                    storage.ip_port,
                    c.immute_domain,
                    storage.instance_role,
                )

    # tendbha proxy use mysqlproxy_up
    cluster_exporter_up_map = query_cluster_exporter_up(DBType.MySQL, "dbm_mysqlproxy_exporter")
    if len(cluster_exporter_up_map) <= 2:
        # 大概率查询异常，忽略
        logger.warning("check_mysqlproxy_exporter_up return less than 2 results: %s", cluster_exporter_up_map)
        return

    for c in Cluster.objects.filter(cluster_type=ClusterType.TenDBHA).prefetch_related(
        "proxyinstance_set", "proxyinstance_set__machine"
    ):
        # 关联 ProxyInstance 表，拿到 bk_biz_id,cluster_domain,host-port,instance_role
        # 然后根据 query_cluster_exporter_up 的查询结果判断 是否上报 mysqlproxy_up 指标
        for proxy in c.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
            # 构造唯一键：appid#cluster_domain#host-port#instance_role
            # 对于 proxy，instance_role 通常是 "proxy"
            unique_key = "{}#{}#{}#{}".format(
                proxy.bk_biz_id,
                c.immute_domain,
                f"{proxy.machine.ip}-{proxy.port}",
                "proxy",  # ProxyInstance 的 instance_role
            )

            # 检查是否在查询结果中
            if unique_key not in cluster_exporter_up_map:
                logger.warning(
                    "ProxyInstance %s (cluster: %s) not reporting mysqlproxy_up metric", proxy.ip_port, c.immute_domain
                )


def check_tendbcluster_exporter_up():
    # tendbcluster backend and proxy both use mysql_up
    tendbcluster_exporter_up_map = query_cluster_exporter_up(DBType.TenDBCluster, "dbm_mysqld_exporter")
    if len(tendbcluster_exporter_up_map) <= 2:
        # 大概率查询异常，忽略
        logger.warning("tendbcluster_exporter_up_map return less than 2 results: %s", tendbcluster_exporter_up_map)
        return

    # 检查 TenDBCluster 集群的 StorageInstance 和 ProxyInstance
    for c in Cluster.objects.filter(cluster_type=ClusterType.TenDBCluster).prefetch_related(
        "storageinstance_set", "storageinstance_set__machine", "proxyinstance_set", "proxyinstance_set__machine"
    ):
        # 检查 StorageInstance
        for storage in c.storageinstance_set.filter(status=InstanceStatus.RUNNING):
            unique_key = "{}#{}#{}#{}".format(
                storage.bk_biz_id, c.immute_domain, f"{storage.machine.ip}-{storage.port}", storage.instance_role
            )

            if unique_key not in tendbcluster_exporter_up_map:
                logger.warning(
                    "StorageInstance %s (cluster: %s, role: %s) not reporting mysql_up metric",
                    storage.ip_port,
                    c.immute_domain,
                    storage.instance_role,
                )

        # 检查 ProxyInstance (TenDBCluster 的 spider 节点也上报 mysql_up)
        for proxy in c.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
            # TenDBCluster 的 proxy 是 spider 节点，需要获取 spider_role
            spider_role = "spider"
            if hasattr(proxy, "tendbclusterspiderext"):
                spider_role = proxy.tendbclusterspiderext.spider_role

            unique_key = "{}#{}#{}#{}".format(
                proxy.bk_biz_id, c.immute_domain, f"{proxy.machine.ip}-{proxy.port}", spider_role
            )

            if unique_key not in tendbcluster_exporter_up_map:
                logger.warning(
                    "ProxyInstance(Spider) %s (cluster: %s, role: %s) not reporting mysql_up metric",
                    proxy.ip_port,
                    c.immute_domain,
                    spider_role,
                )


def check_tendbsingle_exporter_up():
    # tendbsingle use mysql_up
    tendbsingle_exporter_up_map = query_cluster_exporter_up(ClusterType.TenDBSingle, "dbm_mysqld_exporter")
    if len(tendbsingle_exporter_up_map) <= 2:
        # 大概率查询异常，忽略
        logger.warning("tendbsingle_exporter_up_map return less than 2 results: %s", tendbsingle_exporter_up_map)
        return

    # 检查 TenDBSingle 集群的 StorageInstance
    for c in Cluster.objects.filter(cluster_type=ClusterType.TenDBSingle).prefetch_related(
        "storageinstance_set", "storageinstance_set__machine"
    ):
        # 关联 StorageInstance 表，拿到 bk_biz_id,cluster_domain,host-port,instance_role
        # 然后根据 query_cluster_exporter_up 的查询结果判断 是否上报 mysql_up 指标
        for storage in c.storageinstance_set.filter(status=InstanceStatus.RUNNING):
            unique_key = "{}#{}#{}#{}".format(
                storage.bk_biz_id, c.immute_domain, f"{storage.machine.ip}-{storage.port}", storage.instance_role
            )

            if unique_key not in tendbsingle_exporter_up_map:
                logger.warning(
                    "StorageInstance %s (cluster: %s, role: %s) not reporting mysql_up metric",
                    storage.ip_port,
                    c.immute_domain,
                    storage.instance_role,
                )
