import logging
from collections import Counter

from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType, InstanceRole, MachineType
from backend.db_meta.models import AppCache, Cluster, Machine
from backend.db_periodic_task.local_tasks.kafka_check.utils import calculate_kafka_zookeeper_failed_days
from backend.db_report.enums import ReportStateType
from backend.db_report.models import KafkaZookeeperAffinityReport

logger = logging.getLogger("celery")


def check_kafka_zookeeper_affinity():
    """
    检查Kafka Zookeeper节点信息
    1. Zookeeper机房亲和性
    2. Zookeeper机架亲和性
    """
    clusters = Cluster.objects.filter(cluster_type=ClusterType.Kafka)
    for cluster in clusters:
        zk_machines = Machine.objects.filter(
            storageinstance__cluster=cluster,
            storageinstance__instance_role=InstanceRole.ZOOKEEPER,
            machine_type=MachineType.ZOOKEEPER,
        )
        zk_count = zk_machines.count()

        if zk_count == 0:
            logger.warning(f"Kafka cluster {cluster.immute_domain} has no zookeeper instances")
            continue

        # 获取机房和机架分布
        list_rack_id_zk = list(zk_machines.values_list("bk_rack_id", flat=True))
        counter_rack_zk = Counter(list_rack_id_zk)
        list_idc_id_zk = list(zk_machines.values_list("bk_idc_id", flat=True))
        counter_idc_zk = Counter(list_idc_id_zk)

        app = AppCache.objects.get(bk_biz_id=cluster.bk_biz_id).db_app_abbr
        kafka_dba = DBAdministrator().get_biz_db_type_admins(cluster.bk_biz_id, DBType.Kafka)

        state = ReportStateType.NORMAL
        msg = f"Kafka cluster has {zk_count} zookeeper nodes"

        idc_affinity_zk = 0
        rack_affinity_zk = 0

        if zk_count > 0:
            idc_affinity_zk = max(counter_idc_zk.values()) if counter_idc_zk.values() else 0
            rack_affinity_zk = max(counter_rack_zk.values()) if counter_rack_zk.values() else 0

        # 检查机架亲和性，如果机架亲和度大于1，说明有多个节点在同一机架
        if rack_affinity_zk > 1:
            msg += f", rack affinity is {rack_affinity_zk}"
            state = ReportStateType.ABNORMAL
        elif idc_affinity_zk > 1:
            # 机房亲和度暂时只需要记录，不需要warning状态
            msg += f", idc affinity is {idc_affinity_zk}"

        try:
            failed_days = calculate_kafka_zookeeper_failed_days(cluster) if state != ReportStateType.NORMAL else 0
            KafkaZookeeperAffinityReport.objects.create(
                bk_biz_id=cluster.bk_biz_id,
                bk_cloud_id=cluster.bk_cloud_id,
                state=state,
                cluster_type=ClusterType.Kafka,
                zk_node_count=zk_count,
                zk_idc_affinity=idc_affinity_zk,
                zk_rack_affinity=rack_affinity_zk,
                zk_idc_distribution=dict(counter_idc_zk),
                zk_rack_distribution=dict(counter_rack_zk),
                msg=msg,
                domain=cluster.immute_domain,
                app=app,
                dba=kafka_dba,
                failed_days=failed_days,
            )
        except Exception as e:
            logger.error(f"Error occurred while inserting Kafka zookeeper affinity data: {e}")
            raise NotImplementedError(f"{cluster.immute_domain}-{state} insert data failed, msg:{msg}")
