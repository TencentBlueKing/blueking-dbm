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
from backend.db_periodic_task.local_tasks.db_meta.constants import UNIFY_QUERY_PARAMS
from backend.db_periodic_task.local_tasks.mongodb_tasks.report_op import addr, create_failed_record
from backend.db_report.enums.mongodb_check_sub_type import MongodbExporterCheckSubType
from backend.db_report.models.monogdb_check_report import MongodbBackupCheckReport
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, MongoRepository

logger = logging.getLogger("root")


def check_metric():
    r = CheckMongodbUpMetric()
    r.start()


class CheckMongodbUpMetric:
    def __init__(self):
        pass

    def start(self):
        """
        replicaset, sharded cluster 2种架构：
        1, list all cluster
        2, filter failed, write to db
        """

        """
        删除时间大于60天的记录,全备份和binlog都是同一张表，这里操作就好
        """
        failed_records = []
        MongodbBackupCheckReport.objects.filter(create_at__lte=timezone.now() - timedelta(days=60)).delete()

        # 构建查询条件: 集群创建时间大于1小时
        query = Q(cluster_type__in=[ClusterType.MongoShardedCluster, ClusterType.MongoReplicaSet]) & Q(
            create_at__lt=timezone.now() - timedelta(hours=1)
        )
        # 这里的cluster_list是一个QuerySet对象，包含了所有符合条件的Cluster对象
        cluster_list = Cluster.objects.filter(query)
        logger.info(cluster_list.query)

        for c in cluster_list:
            cluster = MongoRepository.fetch_one_cluster(withDomain=False, id=c.id)
            rows = self.check_one(cluster)
            failed_records.extend(rows)

        # 批量插入备份失败记录
        MongodbBackupCheckReport.objects.bulk_create(failed_records)

    @staticmethod
    def check_one(cluster: MongoDBCluster):
        """
        1. 获得所有的mongodb_up的metric.
        2. 对比instance, instance_role 是否一致
        3. 3种失败情况：
            1) metric not found
            2) instance_role not match
            3) value != 1

        """
        failed_records = []
        mongodb_up = MongodbExporterCheckSubType.Up.value

        metric_val = fetch_metric_by_cluster(cluster.immute_domain)
        all_node = get_all_nodes(cluster)
        if len(all_node) == 0:
            # 可能已下架
            return failed_records

        if metric_val is None:
            failed_records.append(
                create_failed_record(
                    c=cluster,
                    shard="",
                    instance="all-node",
                    status=0,
                    msg="fetch metric api error",
                    subtype=mongodb_up,
                )
            )
            return failed_records

        if len(metric_val) == 0:
            failed_records.append(
                create_failed_record(
                    c=cluster, shard="", instance="all-node", status=0, msg="metric not found", subtype=mongodb_up
                )
            )
            return failed_records

        for node in all_node:
            item = metric_val.get(addr(node))
            if item is None:
                msg = "metric not found"
            elif item["value"] != 1:
                msg = "metric value not 1 ({})".format(item["value"])
            elif item["instance_role"] != node.set_name:
                msg = "bad label: instance_role (required: {}, found: {})".format(node.set_name, item["instance_role"])
            else:
                msg = "ok"

            if msg:
                failed_records.append(
                    create_failed_record(
                        c=cluster,
                        shard=node.set_name,
                        instance=addr(node),
                        status=0 if msg != "ok" else 1,
                        msg=msg,
                        subtype=mongodb_up,
                    )
                )

        return failed_records


def get_all_nodes(cluster: MongoDBCluster) -> list:
    """
    获取所有节点的ip和端口
    :param cluster:
    :return:
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
    logger.debug("params: {}".format(params["query_configs"][0]["promql"]))

    metric_result = defaultdict(dict)
    try:
        out = BKMonitorV3Api.unify_query(params, use_admin=True)
        series = out["series"]
    except Exception as e:
        logger.error("query metric error: {}".format(e))
        return None
    logger.debug("cluster_domain: {} series: {}".format(cluster_domain, series))
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
