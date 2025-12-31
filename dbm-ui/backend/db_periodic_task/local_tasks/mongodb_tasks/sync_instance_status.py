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
import time

from django.db.models import Q
from django.utils import timezone

from backend import env
from backend.components import BKMonitorV3Api
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, StorageInstance, MongoDBStorageInstanceExt
from backend.db_periodic_task.local_tasks.db_meta.constants import UNIFY_QUERY_PARAMS
from backend.db_periodic_task.local_tasks.mongodb_tasks.report_op import ClusterReport, RecordBatchOps, addr, dev_debug
from backend.db_report.enums import ReportStateType
from backend.db_report.enums.mongodb_check_sub_type import StorageInstanceStatusCheckSubType
from backend.db_report.repo.task_record_repo import get_report_day_from_time
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, MongoRepository

logger = logging.getLogger("root")


class SyncStorageInstanceStatusTask:
    """同步storage实例的status到db_meta表中"""

    """和巡检任务类似，但执行的频率更高，每2分钟执行一次，要注意不要重复执行"""
    """ # step0: 获得锁，防止重复执行
        # step1: 填充Ext表, 优先级为100.
        # step2: 根据changes(mongodb_mystate)，查到最近2分钟有变化的instance，优先更新
        # step2: 最近更新时间大于5分钟的PRIMARY, 尝试检查并更新.
        # step3: 更新的记录写到mongodb巡检表. """

    check_type: str

    def __init__(self):
        self.check_type = StorageInstanceStatusCheckSubType.SyncStatus.value

    def start(self, report_day: int = None, batch_size: int = 20) -> tuple[int, int, int, int]:
        """
        replicaset, sharded cluster 2种架构：
        1, list all cluster
        2, filter failed, write to db
        """

        # step0: 填充Ext表
        self.fill_ext_table()

        if report_day is None:
            report_day = get_report_day_from_time(timezone.now())
        record_batch_ops = RecordBatchOps(self.check_type, report_day)
        deleted_count = record_batch_ops.delete_old_record(360)
        logger.info(
            f"SyncStorageInstanceStatusTask report_day: {report_day} "
            f"sub_type: {self.check_type} "
            f"deleted_count: {deleted_count}"
        )
        total_num = 0
        try:
            instance_list = self.fetch_latest_changes(minutes=4)
            logger.info(f"fetch_latest_changes: {len(instance_list)} instances")
            # 状态变化 会在同一个shard的多个instance上同时变化，需要合并.
            # 所以这里以shard为单位，查询并合并状态变化.
            # 获得所有的cluster_domain和shard的组合
            cluster_domain_shard_list = list(
                set([instance["cluster_domain"] + ":" + instance["shard"] for instance in instance_list])
            )
            for cluster_domain_shard in cluster_domain_shard_list:
                cluster_domain = cluster_domain_shard.split(":")[0]
                shard = cluster_domain_shard.split(":")[1]
                metric_val = fetch_metric(
                    {
                        "shard": shard,
                        "cluster_domain": cluster_domain,
                    }
                )
                if metric_val is None:
                    logger.error(
                        f"fetch_metric error: metric_val is None for cluster_domain {cluster_domain} and shard {shard}"
                    )
                    continue
        except Exception as e:
            logger.error(f"fetch_latest_changes error: {e}")

        # step2: 最近更新时间大于5分钟的PRIMARY, 检查并更新.
        return

        # 构建查询条件: 集群创建时间大于1小时
        query = Q(cluster_type__in=[ClusterType.MongoShardedCluster, ClusterType.MongoReplicaSet]) & Q(
            create_at__lt=timezone.now() - timedelta(hours=1)
        )
        cluster_list = Cluster.objects.filter(query)
        logger.info(cluster_list.query)
        total_num = 0
        success_num = 0
        warning_num = 0
        abnormal_num = 0
        for i in range(0, len(cluster_list), batch_size):
            for c in cluster_list[i : i + batch_size]:
                cluster = MongoRepository.fetch_one_cluster(with_tags=True, id=c.id)
                rows = self.check_cluster(cluster, report_day)
                total_num += 1
                if rows[0].state == ReportStateType.NORMAL.value:
                    success_num += 1
                elif rows[0].state == ReportStateType.WARNING.value:
                    warning_num += 1
                elif rows[0].state == ReportStateType.ABNORMAL.value:
                    abnormal_num += 1
                for record in rows:
                    record_batch_ops.append(record)
            record_batch_ops.bulk_create()
        logger.info(
            f"SyncStorageInstanceStatusTask report_day: {report_day} "
            f"sub_type: {self.check_type} "
            f"total_num: {total_num}, success_num: {success_num}, warning_num: {warning_num}, abnormal_num: {abnormal_num}"
        )
        return total_num, success_num, warning_num, abnormal_num

    def fill_ext_table(self):
        """
        填充Ext表
        """
        # fetch all instance from db_meta.StorageInstance and without ext
        instance_list = StorageInstance.objects.filter(
            cluster_type__in=[ClusterType.MongoShardedCluster, ClusterType.MongoReplicaSet]
        ).filter(mongodbstorageinstanceext__isnull=True)
        logger.info(f"fill_ext_table: {len(instance_list)} instances")
        if len(instance_list) == 0:
            return
        for instance in instance_list:
            try:
                # fetch instance status from bkmonitor
                ext = MongoDBStorageInstanceExt.objects.create(
                    instance=instance,
                    priority=-1,  # 优先级最低
                    hidden=False,
                    update_at=timezone.now(),
                    state="未检测",
                    state_code=-1,
                )
                logger.info(
                    f"fill_ext_table: {ext.id} {ext.instance.id} {ext.priority} {ext.hidden} {ext.update_at} {ext.state} {ext.state_code}"
                )
            except Exception as e:
                logger.error(f"fill_ext_table error: {e} for instance {instance.machine.ip}:{instance.port}")

    def fetch_latest_changes(self, minutes: int = 4) -> list[dict]:
        """
        获取最近minutes分钟有变化的instance
        changes(bkmonitor:exporter_dbm_mongodb_exporter:mongodb_mongod_replset_my_state[4m]) > 0
        backup instance 的changes 不计算在内
        return list of instance
        """
        end_time = datetime.datetime.now(timezone.utc)
        start_time = end_time - datetime.timedelta(minutes=minutes)
        query_template = {
            "changes": f"changes(bkmonitor:exporter_dbm_mongodb_exporter:mongodb_mongod_replset_my_state{{instance_role!='backup'}}[{minutes}m]) > 0",
        }
        params = copy.deepcopy(UNIFY_QUERY_PARAMS)
        params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
        params["start_time"] = int(start_time.timestamp())
        params["end_time"] = int(end_time.timestamp())
        params["query_configs"][0]["promql"] = query_template["changes"]
        dev_debug("params: {}".format(params["query_configs"][0]["promql"]))
        out = BKMonitorV3Api.unify_query(params, use_admin=True)
        series = out["series"]
        instance_list: list[dict] = []
        for item in series:
            instance = item["dimensions"]["instance"]
            ip_port = item["dimensions"]["bk_target_ip"] + ":" + str(item["dimensions"]["instance_port"])
            new_row = {
                "instance": instance,
                "ip_port": ip_port,
                "instance_role": item["dimensions"]["instance_role"],
                "instance_port": item["dimensions"]["instance_port"],
                "bk_target_ip": item["dimensions"]["bk_target_ip"],
                "cluster_domain": item["dimensions"]["cluster_domain"],
                "shard": item["dimensions"]["shard"],
                "value": item["datapoints"][0][0],
            }
            instance_list.append(new_row)
        return instance_list

    def check_cluster(self, cluster: MongoDBCluster, report_day: int):
        """
        执行_check_cluster_inner, 如果异常，Sleep 10秒后重试，最多试3次
        如果重试3次都失败，则返回异常记录
        """
        last_error = None
        for i in range(3):
            try:
                records = self._do_check_cluster_inner(cluster, report_day)
                if records is not None:
                    return records
            except Exception as e:
                logger.error(f"check_cluster error: {e}, retry {i + 1} times, sleep {i * 3 + 1} seconds")
                last_error = e
                time.sleep(i * 3 + 1)
        cluster_report = ClusterReport(cluster, report_day, self.check_type)
        return cluster_report.make_error_record(f"system error after 3 times retry: {last_error}")


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


def fetch_metric(condition: dict):
    """
    查询mongodb_replset_my_state metric
    return [] or None(error)
    """
    logger.info("fetch_metric condition : {} ".format(condition))
    query_template = {
        "replset_my_state": """avg by (cluster_domain,instance_port,instance_role,instance,bk_target_ip) (
            bkmonitor:exporter_dbm_mongodb_exporter:mongodb_mongod_replset_my_state{condition}
            )""",
    }
    condition_str = ""
    if "cluster_domain" in condition:
        v = condition["cluster_domain"]
        # if v is a list, join with "|"
        if isinstance(v, list):
            v = "^(" + "|".join(v) + ")$"
            condition_str = f"cluster_domain=~{v}"
        else:
            condition_str = f'cluster_domain="{v}"'
    elif "instance" in condition:
        v = condition["instance"]
        if isinstance(v, list):
            v = "^(" + "|".join(v) + ")$"
            condition_str = f"instance=~{v}"
        else:
            condition_str = f'instance="{v}"'
    elif "instance_host" in condition:
        v = condition["instance_host"]
        if isinstance(v, list):
            v = "^(" + "|".join(v) + ")$"
            condition_str = f"instance_host=~{v}"
        else:
            condition_str = f'instance_host="{v}"'
    else:
        raise ValueError("condition is invalid")
    #
    # now-5/15m ~ now
    end_time = datetime.datetime.now(timezone.utc)
    start_time = end_time - datetime.timedelta(minutes=5)
    params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    params["start_time"] = int(start_time.timestamp())
    params["end_time"] = int(end_time.timestamp())
    # 设置要查询的 cluster_domain 变量
    params["query_configs"][0]["promql"] = query_template["replset_my_state"].format(condition=condition_str)
    dev_debug("params: {}".format(params["query_configs"][0]["promql"]))

    metric_result = defaultdict(dict)
    try:
        out = BKMonitorV3Api.unify_query(params, use_admin=True)
        series = out["series"]
    except Exception as e:
        logger.error("query metric error: {}".format(e))
        return None
    dev_debug("series: {}".format(series))
    for item in series:
        logger.info("item: {}".format(item))
        ip_port = item["dimensions"]["bk_target_ip"] + ":" + str(item["dimensions"]["instance_port"])
        logger.info("ip_port: {}".format(ip_port))
        metric_result[ip_port] = {
            "instance": ip_port,
            "instance_role": item["dimensions"]["instance_role"],
            "instance_port": item["dimensions"]["instance_port"],
            "bk_target_ip": item["dimensions"]["bk_target_ip"],
            "cluster_domain": item["dimensions"]["cluster_domain"],
            "value": item["datapoints"][0][0],
        }
    return metric_result
