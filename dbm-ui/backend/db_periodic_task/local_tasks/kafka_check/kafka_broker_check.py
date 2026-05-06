import logging
from collections import Counter

from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType, InstanceRole, MachineType
from backend.db_meta.models import AppCache, Cluster, Machine
from backend.db_periodic_task.local_tasks.kafka_check.utils import calculate_kafka_broker_failed_days
from backend.db_report.enums import ReportStateType
from backend.db_report.models import KafkaBrokerAffinityReport

logger = logging.getLogger("celery")


def check_kafka_broker_affinity():
    """
    检查Kafka Broker节点信息
    1. Broker机架亲和性
    """
    clusters = Cluster.objects.filter(cluster_type=ClusterType.Kafka)
    for cluster in clusters:
        broker_machines = Machine.objects.filter(
            storageinstance__cluster=cluster,
            storageinstance__instance_role=InstanceRole.BROKER,
            machine_type=MachineType.BROKER,
        )
        broker_count = broker_machines.count()

        if broker_count == 0:
            logger.warning(f"Kafka cluster {cluster.immute_domain} has no broker instances")
            continue

        # 获取机架分布
        list_rack_id_broker = list(broker_machines.values_list("bk_rack_id", flat=True))
        counter_rack_broker = Counter(list_rack_id_broker)

        app = AppCache.objects.get(bk_biz_id=cluster.bk_biz_id).db_app_abbr
        kafka_dba = DBAdministrator().get_biz_db_type_admins(cluster.bk_biz_id, DBType.Kafka)

        state = ReportStateType.NORMAL
        msg = f"Kafka cluster has {broker_count} broker nodes"

        rack_affinity_broker = 0

        if broker_count > 0:
            rack_affinity_broker = max(counter_rack_broker.values()) if counter_rack_broker.values() else 0

        # 检查机架亲和性，如果机架亲和度大于1，说明有多个节点在同一机架
        if rack_affinity_broker > 1:
            msg += f", rack affinity is {rack_affinity_broker}"
            state = ReportStateType.WARNING

        try:
            failed_days = calculate_kafka_broker_failed_days(cluster) if state != ReportStateType.NORMAL else 0
            KafkaBrokerAffinityReport.objects.create(
                bk_biz_id=cluster.bk_biz_id,
                bk_cloud_id=cluster.bk_cloud_id,
                state=state,
                cluster_type=ClusterType.Kafka,
                broker_node_count=broker_count,
                broker_rack_affinity=rack_affinity_broker,
                broker_rack_distribution=dict(counter_rack_broker),
                msg=msg,
                domain=cluster.immute_domain,
                app=app,
                dba=kafka_dba,
                failed_days=failed_days,
            )
        except Exception as e:
            logger.error(f"Error occurred while inserting Kafka broker affinity data: {e}")
            raise NotImplementedError(f"{cluster.immute_domain}-{state} insert data failed, msg:{msg}")
