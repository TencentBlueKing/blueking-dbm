import logging
from collections import Counter

from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType, InstanceRole, MachineType
from backend.db_meta.models import AppCache, Cluster, Machine
from backend.db_report.enums import ReportStateType
from backend.db_report.models import EsDatanodeReport

logger = logging.getLogger("celery")


def check_es_datanode():
    """
    检查ES 数据节点信息
    1. 热节点机架亲合度
    2. 热节点机房亲合度
    3. 冷节点机房亲合度
    4. 冷节点机房亲合度
    """
    clusters = Cluster.objects.filter(cluster_type=ClusterType.Es)
    for cluster in clusters:
        hot_machines = Machine.objects.filter(
            storageinstance__cluster=cluster,
            storageinstance__instance_role=InstanceRole.ES_DATANODE_HOT,
            machine_type=MachineType.ES_DATANODE,
        )
        hot_count = hot_machines.count()
        list_rack_id_hot = list(hot_machines.values_list("bk_rack_id", flat=True))
        counter_rack_hot = Counter(list_rack_id_hot)
        list_idc_id_hot = list(hot_machines.values_list("bk_idc_id", flat=True))
        counter_idc_hot = Counter(list_idc_id_hot)

        cold_machines = Machine.objects.filter(
            storageinstance__cluster=cluster,
            storageinstance__instance_role=InstanceRole.ES_DATANODE_COLD,
            machine_type=MachineType.ES_DATANODE,
        )
        cold_count = cold_machines.count()
        list_rack_id_cold = list(cold_machines.values_list("bk_rack_id", flat=True))
        counter_rack_cold = Counter(list_rack_id_cold)
        list_idc_id_cold = list(cold_machines.values_list("bk_idc_id", flat=True))
        counter_idc_cold = Counter(list_idc_id_cold)

        app = AppCache.objects.get(bk_biz_id=cluster.bk_biz_id).db_app_abbr
        es_dba = DBAdministrator().get_biz_db_type_admins(cluster.bk_biz_id, DBType.Es)

        state = ReportStateType.NORMAL
        msg = f"ES cluster has {hot_count} hot machines, {cold_count} cold machines"

        idc_affinity_hot = 0
        rack_affinity_hot = 0
        idc_affinity_cold = 0
        rack_affinity_cold = 0
        if hot_count > 0:
            idc_affinity_hot = max(counter_idc_hot.values())
            rack_affinity_hot = max(counter_rack_hot.values())
        if cold_count > 0:
            idc_affinity_cold = max(counter_idc_cold.values())
            rack_affinity_cold = max(counter_rack_cold.values())

        if rack_affinity_hot > 1 or rack_affinity_cold > 1:
            msg += f", hot rack affinity is {rack_affinity_hot}"
            msg += f", cold rack affinity is {rack_affinity_cold}"
            state = ReportStateType.NORMAL.WARNING
        elif idc_affinity_hot > 1 or idc_affinity_cold > 1:
            # 机房亲合度暂时不需要warning状态
            msg += f", hot idc affinity is {idc_affinity_hot}"
            msg += f", cold idc affinity is {idc_affinity_cold}"

        try:
            EsDatanodeReport.objects.create(
                bk_biz_id=cluster.bk_biz_id,
                bk_cloud_id=cluster.bk_cloud_id,
                state=state,
                cluster_type=ClusterType.Es,
                idc_affinity_hot=idc_affinity_hot,
                rack_affinity_hot=rack_affinity_hot,
                idc_affinity_cold=idc_affinity_cold,
                rack_affinity_cold=rack_affinity_cold,
                msg=msg,
                domain=cluster.immute_domain,
                app=app,
                dba=es_dba,
            )
        except Exception as e:
            logger.error(f"Error occurred while inserting data: {e}")
            raise NotImplementedError("{}-{} insert data failed, msg:{}".format(cluster.immute_domain, state, msg))
