import logging

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.exceptions import ClusterNotExistException, DBMetaException
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.db_meta.sync_cluster_stat import query_capacity_for_clusters
from backend.flow.engine.bamboo.scene.mysql.common.statsdb_client import DB_QUERY_TEMPLATE, StatsDBClient

logger = logging.getLogger("root")
ALLOW_DISK_USE_PERCENT = 0.8


def assess_disk_space_for_migration(
    bk_biz_id: int, cluster_type: str, migrations: list = None, factor: int = 1
) -> dict:
    """
    评估DB迁移，目标集群磁盘空间是否充足
    @param bk_biz_id: 业务id
    @param cluster_type: 集群类型
    @param factor: 按照几倍于待迁移db的大小，评估空间，默认为1；
                   某些场景，比如先克隆，后抽数导入，需要两倍于待迁移db大小的空间，设置为2
    @param migrations: db迁移任务列表
    """
    from collections import defaultdict

    multi_instance = defaultdict(list)  # ip -> immute_domain list
    same_target_host = defaultdict(list)  # ip -> migration index list
    db_size = []  # index -> db size sum
    disk_size = defaultdict(dict)  # ip -> {'used': x, 'total': y}
    target_domains = []
    not_enough = []
    result = {}
    client = StatsDBClient()
    try:
        for number, info in enumerate(migrations):
            source = Cluster.objects.get(id=info["source_cluster"], bk_biz_id=bk_biz_id)
            dbs = info["db_list"]
            placeholders = ",".join(["%s"] * len(dbs))
            query_template = DB_QUERY_TEMPLATE.get("DBSIZE").replace("IN (%s)", "IN ({})".format(placeholders))
            resp = client.query(query_template, [source.immute_domain] + dbs)
            if len(resp) != len(info["db_list"]):
                msg = _("缺少[{}]集群[{}]数据库大小最近1天的统计信息".format(source.immute_domain, dbs))
                result["error"] = msg
                logger.error(msg)
                return result
            db_size.append(sum(item["bytes"] for item in resp))
            for cluster in info["target_clusters"]:
                target = __get_cluster_info(cluster_id=cluster, bk_biz_id=bk_biz_id)
                multi_instance[target["ip"]].append(target["immute_domain"])
                same_target_host[target["ip"]].append(number)
                target_domains.append(target["immute_domain"])
    finally:
        client.close()

    logger.info("query_cluster_capacity started")
    try:
        all_disk_size = query_capacity_for_clusters(bk_biz_id, cluster_type, list(set(target_domains)))
    except Exception as e:
        msg = _("业务[{}]集群类型[{}]最新统计信息获取失败:[{}]".format(bk_biz_id, cluster_type, e))
        result["error"] = msg
        logger.error(msg)
        return result
    for ip, clusters in multi_instance.items():
        first_domain = clusters[0]
        disk_size[ip]["used"] = all_disk_size[first_domain]["used"]
        disk_size[ip]["total"] = all_disk_size[first_domain]["total"]
        db_total = sum(db_size[number] for number in same_target_host[ip])
        # used + factor * to_be_migrated > ALLOW_DISK_USE_PERCENT * total
        if factor * disk_size[ip]["used"] + db_total > disk_size[ip]["total"] * ALLOW_DISK_USE_PERCENT:
            logger.info(_("ip[{}] domain[{}]空间不足".format(ip, list(set(multi_instance[ip])))))
            not_enough.extend(same_target_host[ip])
        else:
            logger.info(_("ip[{}] domain[{}]有足够的空间".format(ip, list(set(multi_instance[ip])))))
        result["not_enough"] = sorted(list(set(not_enough)))
    return result


def __get_cluster_info(cluster_id: int, bk_biz_id: int) -> dict:
    """
    获取集群域名与主库ip
    @param cluster_id: 集群cluster_id
    @param bk_biz_id: 业务id
    """
    try:
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
    except Cluster.DoesNotExist:
        raise ClusterNotExistException(cluster_id=cluster_id, bk_biz_id=bk_biz_id, message=_("集群不存在"))
    if cluster.cluster_type == ClusterType.TenDBHA.value:
        ip_port = cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER).ip_port
    elif cluster.cluster_type == ClusterType.TenDBSingle.value:
        ip_port = cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.ORPHAN).ip_port
    else:
        raise DBMetaException(message=_("不支持的集群类型"))
    return {
        "immute_domain": cluster.immute_domain,
        "ip": ip_port.split(":")[0],
    }
