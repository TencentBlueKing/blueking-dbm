import copy
import logging
import time

from django.utils.translation import gettext as _

from backend import env
from backend.components import BKMonitorV3Api
from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache, Cluster
from backend.db_monitor.constants import ES_DAILY_CHECK_TEMPLATE
from backend.db_periodic_task.local_tasks.db_meta.constants import UNIFY_QUERY_PARAMS
from backend.db_report.enums import ReportStateType
from backend.db_report.models.es_status_report import EsStatusReport

logger = logging.getLogger("celery")


def query_cluster_status(status):
    """查询某类集群的 exporter 是否正常"""
    # 获取查询模板
    query_template = ES_DAILY_CHECK_TEMPLATE.get("cluster_status")

    # 查询业务固定为DBA，查询时间取模板range
    params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    params["end_time"] = int(time.time())
    params["start_time"] = params["end_time"] - int(query_template["range"]) * 60
    promql_filter = 'color="{}"'.format(status)
    params["query_configs"][0]["promql"] = query_template["template"] % promql_filter

    # 查询指标
    try:
        series = BKMonitorV3Api.unify_query(params, use_admin=True)["series"]
    except Exception as e:
        logger.error(f"Error occurred while doing BKMonitorV3Api.unify_query(: {e}")
        raise NotImplementedError("Get cluster status={} failed from BKMonitorV3Api ".format(status))

    clusters = []
    for item in series:
        # 获取的五个点，如果有一个为1，则认为集群状态异常
        for value, tmp in item["datapoints"]:
            if value == 1:
                clusters.append(item["dimensions"])
                break
    return clusters


def write_to_db_report(domain, status):
    cluster = Cluster.objects.get(immute_domain=domain)
    app = AppCache.objects.get(bk_biz_id=cluster.bk_biz_id).db_app_abbr
    es_dba = DBAdministrator().get_biz_db_type_admins(cluster.bk_biz_id, DBType.Es)
    try:
        EsStatusReport.objects.create(
            bk_biz_id=cluster.bk_biz_id,
            bk_cloud_id=cluster.bk_cloud_id,
            state=status,
            cluster_type=ClusterType.Es,
            msg=f"ES cluster status is {status}",
            domain=cluster.immute_domain,
            app=app,
            dba=es_dba,
        )
        logger.warning(_("+===+++++=== 集群 {} 状态为 {}  +++++===++++ ".format(domain, status)))
    except Exception as e:
        logger.error(f"Error occurred while inserting data: {e}")
        raise NotImplementedError("{}-{} insert data failed".format(domain, status))


def check_es_status():
    """
    检查ES集群状态为red和yellow
    """
    clusters_red = query_cluster_status(status="red")
    for cluster in clusters_red:
        domain = cluster["cluster_domain"]
        write_to_db_report(domain, ReportStateType.ABNORMAL)

    clusters_yellow = query_cluster_status(status="yellow")
    for cluster in clusters_yellow:
        domain = cluster["cluster_domain"]
        write_to_db_report(domain, ReportStateType.WARNING)
