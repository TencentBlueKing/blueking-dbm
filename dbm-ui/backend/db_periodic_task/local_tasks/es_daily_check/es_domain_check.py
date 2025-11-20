import logging

from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterEntryType, ClusterType
from backend.db_meta.models import AppCache, Cluster, ClusterEntry
from backend.db_report.enums import ReportStateType
from backend.db_report.models.es_domain_report import EsDomainReport
from backend.flow.engine.bamboo.scene.es.atom_jobs.access_manager import (
    get_access_ips_from_clb,
    get_access_ips_from_dbmeta,
    get_access_ips_from_dns,
    get_access_ips_from_polaris,
)

logger = logging.getLogger("celery")


def check_es_domain():
    """
    检查ES域名映射
    """
    clusters = Cluster.objects.filter(cluster_type=ClusterType.Es)
    for cluster in clusters:
        app = AppCache.objects.get(bk_biz_id=cluster.bk_biz_id).db_app_abbr
        es_dba = DBAdministrator().get_biz_db_type_admins(cluster.bk_biz_id, DBType.Es)
        state = ReportStateType.NORMAL

        cluster_entries = ClusterEntry.objects.filter(cluster__id=cluster.id)
        access_ip_set_from_dbmeta = set(get_access_ips_from_dbmeta(cluster_id=cluster.id))
        for ce in cluster_entries:
            if ce.forward_to_id is None:
                if ce.cluster_entry_type == ClusterEntryType.DNS:
                    access_ip_set_from_dns = set(
                        get_access_ips_from_dns(
                            bk_cloud_id=cluster.bk_cloud_id, bk_biz_id=cluster.bk_biz_id, domain=cluster.immute_domain
                        )
                    )
                    if access_ip_set_from_dbmeta != access_ip_set_from_dns:
                        state = ReportStateType.ABNORMAL
                        msg = f"domain ips: {str(access_ip_set_from_dns)}, but not {str(access_ip_set_from_dbmeta)}"
                    else:
                        msg = "domain is right"
                elif ce.cluster_entry_type == ClusterEntryType.CLB:
                    access_ip_set_from_clb = set(get_access_ips_from_clb(clb_ip=ce.entry))
                    if access_ip_set_from_dbmeta != access_ip_set_from_clb:
                        state = ReportStateType.ABNORMAL
                        msg = f"clb ips: {str(access_ip_set_from_clb)}, but not {str(access_ip_set_from_dbmeta)}"
                    else:
                        msg = "clb is right"
                elif ce.cluster_entry_type == ClusterEntryType.POLARIS:
                    access_ip_set_from_polaris = set(get_access_ips_from_polaris(service_name=ce.entry))
                    if access_ip_set_from_dbmeta != access_ip_set_from_polaris:
                        state = ReportStateType.ABNORMAL
                        msg = (
                            f"polaris ips: {str(access_ip_set_from_polaris)}, but not {str(access_ip_set_from_dbmeta)}"
                        )
                    else:
                        msg = "polaris is right"
                else:
                    return

                try:
                    EsDomainReport.objects.create(
                        bk_biz_id=cluster.bk_biz_id,
                        bk_cloud_id=cluster.bk_cloud_id,
                        state=state,
                        cluster_type=ClusterType.Es,
                        msg=msg,
                        domain=ce.entry,
                        app=app,
                        dba=es_dba,
                        type=ce.cluster_entry_type,
                    )
                except Exception as e:
                    logger.error(f"Error occurred while inserting data: {e}")
                    raise NotImplementedError(
                        "{}-{} insert data failed, msg:{}".format(cluster.immute_domain, state, msg)
                    )
