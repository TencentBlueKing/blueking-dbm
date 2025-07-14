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
import datetime
import logging
from collections import defaultdict
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from backend import env
from backend.components import BKMonitorV3Api
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_meta.models.app import TenantCache
from backend.db_periodic_task.local_tasks.db_meta.constants import UNIFY_QUERY_PARAMS
from backend.db_periodic_task.local_tasks.mongodb_tasks.report_op import ClusterReport, RecordBatchOps, addr, dev_debug
from backend.db_report.enums import ReportStateType
from backend.db_report.enums.mongodb_check_sub_type import MongodbExporterCheckSubType
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, MongoRepository

logger = logging.getLogger("root")


class CheckMongodbUpMetricTask:
    """检查mongodb_up指标, 每个节点的mongodb_up指标值为1, 否则认为异常"""

    check_type: str

    def __init__(self):
        self.check_type = MongodbExporterCheckSubType.Up.value

    def start(self, report_day: int = None, batch_size: int = 20):
        """
        replicaset, sharded cluster 2种架构：
        1, list all cluster
        2, filter failed, write to db
        """
        if report_day is None:
            report_day = int(timezone.now().date().strftime("%Y%m%d"))
        record_batch_ops = RecordBatchOps(self.check_type, report_day)
        deleted_count = record_batch_ops.delete_old_record(360)
        logger.info(
            f"CheckMongodbUpMetricTask report_day: {report_day} "
            f"sub_type: {self.check_type} "
            f"deleted_count: {deleted_count}"
        )
        deleted_count = record_batch_ops.delete_today_record()
        logger.info(
            f"CheckMongodbUpMetricTask report_day: {report_day} "
            f"sub_type: {self.check_type} "
            f"deleted_count: {deleted_count}"
        )

        # 构建查询条件: 集群创建时间大于1小时
        query = Q(cluster_type__in=[ClusterType.MongoShardedCluster, ClusterType.MongoReplicaSet]) & Q(
            create_at__lt=timezone.now() - timedelta(hours=1)
        )
        cluster_list = Cluster.objects.filter(query)
        logger.info(cluster_list.query)
        app_total = {
            ReportStateType.NORMAL.value: 0,
            ReportStateType.WARNING.value: 0,
            ReportStateType.ABNORMAL.value: 0,
        }

        for i in range(0, len(cluster_list), batch_size):
            for c in cluster_list[i : i + batch_size]:
                cluster = MongoRepository.fetch_one_cluster(with_tags=True, id=c.id)
                rows = self.check_cluster(cluster, report_day)
                app_total[rows[0].state] += 1
                for record in rows:
                    record_batch_ops.append(record)
            record_batch_ops.bulk_create()
        logger.info(
            f"CheckMongodbUpMetricTask report_day: {report_day} "
            f"sub_type: {self.check_type} "
            f"app_total: {app_total}"
        )

    def is_skip_check(self, cluster: MongoDBCluster) -> tuple[bool, str]:
        """
        检查集群的tags是否为skip_check=true
        如果为true，则返回True, "skipped by skip_check:true"
        如果为false，则返回False, ""
        """
        tags = {tag.key: tag.value for tag in cluster.tags} if cluster.tags else {}
        v = tags.get("temporary", "")
        if v in ["true", "yes", "True", "Yes", "1"]:
            return True, "skipped by temporary:{}".format(v)
        return False, ""

    def check_cluster(self, cluster: MongoDBCluster, report_day: int):
        """
        1. 获得所有的mongodb_up的metric.
        2. 对比instance, instance_role 是否一致
        3. 3种失败情况：
            1) metric not found
            2) instance_role not match
            3) value != 1
        """
        cluster_report = ClusterReport(cluster, report_day, self.check_type)

        skipped, reason = self.is_skip_check(cluster)
        if skipped:
            dev_debug(f"=== check_one {cluster.cluster_id} {cluster.immute_domain} {reason} === ")
            return cluster_report.make_skip_record(reason)

        all_node = get_all_nodes(cluster)
        if len(all_node) == 0:
            cluster_report.append(ReportStateType.ABNORMAL.value, "all", "all", "no node")
            return cluster_report.make_records()

        metric_val = fetch_metric_by_cluster(cluster.immute_domain)
        for node in all_node:
            msg = "ok"
            item = metric_val.get(addr(node))
            if item is None:
                msg = "metric not found"
                state = ReportStateType.ABNORMAL.value
            elif item["value"] != 1:
                msg = "metric value not 1 ({})".format(item["value"])
                state = ReportStateType.ABNORMAL.value
            else:
                msg = "ok"
                state = ReportStateType.NORMAL.value

            cluster_report.append(state, node.set_name, addr(node), msg)

        return cluster_report.make_records()


def get_all_nodes(cluster: MongoDBCluster) -> list:
    """
    获取所有节点的ip和端口
    """
    nodes = []
    for shard in cluster.get_shards(with_config=True, sort_by_set_name=True):
        for node in shard.members:
            node.__setattr__("set_name", shard.set_name)
            node.__setattr__("instance_role", node.role)
            nodes.append(node)

    if cluster.is_sharded_cluster():
        for node in cluster.get_mongos():
            node.__setattr__("set_name", "mongos")
            node.__setattr__("instance_role", node.role)
            nodes.append(node)

    return nodes


def fetch_metric_by_cluster(cluster_domain):
    """
    查询集群的mongodb_up metric
    return [] or None(error)
    """
    logger.info("fetch_metric_by_cluster cluster : {} ".format(cluster_domain))
    query_template = {
        "up": """sum by (cluster_domain,instance,instance_role,instance_port,bk_target_ip) (
            bkmonitor:exporter_dbm_mongodb_exporter:mongodb_up{{cluster_domain="{cluster_domain}"}}
            )""",
        "disk": """sum by (cluster_domain,instance,instance_role,instance_port,bk_target_ip) (
            bkmonitor:dbm_system:disk:in_use{{cluster_domain="{cluster_domain}"}}
            )""",
    }
    #
    # now-5/15m ~ now
    end_time = datetime.datetime.now(timezone.utc)
    start_time = end_time - datetime.timedelta(minutes=5)
    params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    params["start_time"] = int(start_time.timestamp())
    params["end_time"] = int(end_time.timestamp())
    # 设置要查询的 cluster_domain 变量
    params["query_configs"][0]["promql"] = query_template["up"].format(cluster_domain=cluster_domain)
    dev_debug("params: {}".format(params["query_configs"][0]["promql"]))

    tenant_id = TenantCache.get_tenant_with_app(params["bk_biz_id"])
    params["tenant_id"] = tenant_id

    metric_result = defaultdict(dict)
    try:
        out = BKMonitorV3Api.unify_query(params, use_admin=True)
        series = out["series"]
    except Exception as e:
        logger.error("query metric error: {}".format(e))
        return None
    dev_debug("cluster_domain: {} series: {}".format(cluster_domain, series))
    for item in series:
        logger.info("cluster_domain: {} item: {}".format(cluster_domain, item))
        ip_port = item["dimensions"]["bk_target_ip"] + ":" + str(item["dimensions"]["instance_port"])
        logger.info("cluster_domain: {} ip_port: {}".format(cluster_domain, ip_port))
        metric_result[ip_port] = {
            "instance": ip_port,
            "instance_role": item["dimensions"]["instance_role"],
            "instance_port": item["dimensions"]["instance_port"],
            "bk_target_ip": item["dimensions"]["bk_target_ip"],
            "cluster_domain": item["dimensions"]["cluster_domain"],
            "value": item["datapoints"][0][0],
        }
    return metric_result
