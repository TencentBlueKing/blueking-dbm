import logging
from collections import Counter

from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import AppCache, Cluster, Machine
from backend.db_report.enums import ReportStateType
from backend.db_report.models.es_master_report import EsMasterReport

logger = logging.getLogger("celery")


def check_es_master():
    """
    检查ES master节点信息
    1. master节点数量
    2. master机架亲合度
    3. master机房亲合度
    """
    clusters = Cluster.objects.filter(cluster_type=ClusterType.Es)
    for cluster in clusters:
        master_machines = Machine.objects.filter(storageinstance__cluster=cluster, machine_type=MachineType.ES_MASTER)
        master_count = master_machines.count()
        list_rack_id = list(master_machines.values_list("bk_rack_id", flat=True))
        counter_rack = Counter(list_rack_id)
        list_idc_id = list(master_machines.values_list("bk_idc_id", flat=True))
        counter_idc = Counter(list_idc_id)
        list_ip = list(master_machines.values_list("ip", flat=True))

        app = AppCache.objects.get(bk_biz_id=cluster.bk_biz_id).db_app_abbr
        es_dba = DBAdministrator().get_biz_db_type_admins(cluster.bk_biz_id, DBType.Es)

        state = ReportStateType.NORMAL
        msg = f"ES cluster has {master_count} masters, master_ips: {list_ip}"
        # 当前部署使用3个master
        if master_count != 3:
            state = ReportStateType.ABNORMAL
        else:
            if max(counter_rack.values()) > 1:
                msg += f", rack affinity is {max(counter_rack.values())}"
                state = ReportStateType.WARNING
            elif max(counter_idc.values()) > 1:
                msg += f", idc affinity is {max(counter_idc.values())}"
                state = ReportStateType.WARNING

        try:
            EsMasterReport.objects.create(
                bk_biz_id=cluster.bk_biz_id,
                bk_cloud_id=cluster.bk_cloud_id,
                state=state,
                cluster_type=ClusterType.Es,
                master_count=master_count,
                idc_affinity=max(counter_idc.values()),
                rack_affinity=max(counter_rack.values()),
                msg=msg,
                domain=cluster.immute_domain,
                app=app,
                dba=es_dba,
            )
        except Exception as e:
            logger.error(f"Error occurred while inserting data: {e}")
            raise NotImplementedError("{}-{} insert data failed, msg:{}".format(cluster.immute_domain, state, msg))
