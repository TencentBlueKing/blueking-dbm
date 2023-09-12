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
import json
import logging
import operator
from collections import defaultdict
from datetime import datetime, timedelta
from functools import reduce
from typing import Any, Dict, List

from celery import shared_task
from celery.result import AsyncResult
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from backend import env
from backend.components import BKLogApi
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.ticket.builders.common.constants import MYSQL_CHECKSUM_TABLE, MySQLDataRepairTriggerMode
from backend.ticket.constants import FlowErrCode, TicketType
from backend.ticket.flow_manager.inner import InnerFlow
from backend.ticket.models.ticket import Flow, Ticket
from backend.utils.time import datetime2str

logger = logging.getLogger("root")


class TicketTask(object):
    """关联单据的异步任务集合类"""

    def __init__(self, ticket_id: int) -> None:
        self.ticket = Ticket.objects.get(id=ticket_id)

    def run_next_flow(self) -> None:
        """调用单据下一流程"""
        logger.info(f"{self.ticket.current_flow().flow_alias} has done, run next flow....")

        from backend.ticket.flow_manager.manager import TicketFlowManager

        TicketFlowManager(ticket=self.ticket).run_next_flow()

    @classmethod
    def retry_exclusive_inner_flow(cls) -> None:
        """重试互斥错误的inner flow"""
        to_retry_flows = Flow.objects.filter(err_code=FlowErrCode.AUTO_EXCLUSIVE_ERROR)
        if not to_retry_flows:
            return

        logger.info(
            f"Automatically retry the mutually exclusive flow, "
            f"there are still {to_retry_flows.count()} flows waiting to be retried...."
        )

        for flow in to_retry_flows:
            InnerFlow(flow_obj=flow).retry()

    @classmethod
    def _create_ticket(cls, ticket_type, creator, bk_biz_id, remark, details) -> None:
        """创建一个新单据"""
        Ticket.create_ticket(
            ticket_type=ticket_type, creator=creator, bk_biz_id=bk_biz_id, remark=remark, details=details
        )

    @classmethod
    def auto_create_data_repair_ticket(cls):
        """根据例行校验的结果自动创建修复单据"""

        # 例行时间校验默认间隔一天
        now = datetime.now()
        start_time, end_time = datetime2str(now - timedelta(days=1)), datetime2str(now)
        resp = BKLogApi.esquery_search(
            {
                "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.mysql_checksum_result",
                "start_time": start_time,
                "end_time": end_time,
                "query_string": "*",
                "start": 0,
                "size": 1000,
                "sort_list": [["dtEventTimeStamp", "asc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
            }
        )

        # 根据集群ID聚合日志
        cluster__checksum_logs_map: Dict[int, List[Dict]] = defaultdict(list)
        for hit in resp["hits"]["hits"]:
            checksum_log = json.loads(hit["_source"]["log"])
            cluster__checksum_logs_map[checksum_log["cluster_id"]].append(checksum_log)

        # 为每个待修复的集群生成修复单据
        for cluster_id, checksum_logs in cluster__checksum_logs_map.items():
            try:
                cluster = Cluster.objects.get(id=cluster_id)
            except Cluster.DoesNotExist:
                # 忽略不在dbm meta信息中的集群
                logger.error(_("无法在dbm meta中查询到集群{}的相关信息，请排查该集群的状态".format(cluster_id)))
                continue

            inst_filter_list = [
                (
                    Q(
                        cluster=cluster,
                        machine__ip=log["ip"],
                        port=log["port"],
                        instance_inner_role=InstanceInnerRole.SLAVE,
                    )
                    | Q(
                        cluster=cluster,
                        machine__ip=log["master_ip"],
                        port=log["master_port"],
                        instance_inner_role=InstanceInnerRole.MASTER,
                    )
                )
                for log in checksum_logs
            ]
            inst_filters = reduce(operator.or_, inst_filter_list)
            ip_port__instance_id_map: Dict[str, StorageInstance] = {
                f"{inst.machine.ip}:{inst.port}": inst
                for inst in StorageInstance.objects.select_related("machine").filter(inst_filters)
            }

            data_repair_infos: List[Dict[str, Any]] = []
            master_slave_exists: Dict[str, Dict[str, bool]] = defaultdict(lambda: defaultdict(bool))
            for log in checksum_logs:
                master_ip_port, slave_ip_port = (
                    f"{log['master_ip']}:{log['master_port']}",
                    f"{log['ip']}:{log['port']}",
                )
                # 如果在meta信息中查询不出master或slave，则跳过
                if (
                    master_ip_port not in ip_port__instance_id_map.keys()
                    or slave_ip_port not in ip_port__instance_id_map.keys()
                ):
                    continue

                # 如果数据校验一致 or 重复的主从对，则跳过
                is_consistent = log["master_crc"] == log["this_crc"] and log["master_cnt"] == log["this_cnt"]
                if is_consistent or master_slave_exists[master_ip_port][slave_ip_port]:
                    continue

                # 标记需要检验的master/slave，并缓存到修复信息中
                master_slave_exists[master_ip_port][slave_ip_port] = True
                master = ip_port__instance_id_map[master_ip_port]
                master_data_repair_info = {
                    "id": master.id,
                    "bk_biz_id": log["bk_biz_id"],
                    "ip": log["master_ip"],
                    "port": log["master_port"],
                    "bk_host_id": master.machine.bk_host_id,
                    "bk_cloud_id": master.machine.bk_cloud_id,
                }
                slave = ip_port__instance_id_map[slave_ip_port]
                slave_data_repair_info = {
                    "id": slave.id,
                    "bk_biz_id": log["bk_biz_id"],
                    "ip": log["ip"],
                    "port": log["port"],
                    "bk_host_id": slave.machine.bk_host_id,
                    "bk_cloud_id": slave.machine.bk_cloud_id,
                    "is_consistent": is_consistent,
                }
                # 注意这里要区别集群类型
                if cluster.cluster_type == ClusterType.TenDBCluster or not data_repair_infos:
                    data_repair_infos.append({"master": master_data_repair_info, "slaves": [slave_data_repair_info]})
                elif cluster.cluster_type == ClusterType.TenDBHA:
                    data_repair_infos[0]["slaves"].append(slave_data_repair_info)

            # 如果不存在需要修复的slave，则跳过
            if not data_repair_infos:
                logger.info(_("集群{}数据校验正确，不需要进行数据修复".format(cluster_id)))
                continue

            # 构造修复单据
            ticket_details = {
                # "非innodb表是否修复"这个参数与校验保持一致，默认为false
                "is_sync_non_innodb": False,
                "is_ticket_consistent": False,
                "checksum_table": MYSQL_CHECKSUM_TABLE,
                "trigger_type": MySQLDataRepairTriggerMode.ROUTINE.value,
                "start_time": start_time,
                "end_time": end_time,
                "infos": [
                    {
                        "cluster_id": cluster_id,
                        "master": data_info["master"],
                        "slaves": data_info["slaves"],
                    }
                    for data_info in data_repair_infos
                ],
            }
            ticket_type = TicketType.MYSQL_DATA_REPAIR
            if cluster.cluster_type == ClusterType.TenDBCluster:
                ticket_type = TicketType.TENDBCLUSTER_DATA_REPAIR
            cls._create_ticket(
                ticket_type=ticket_type,
                creator=cluster.creator,
                bk_biz_id=cluster.bk_biz_id,
                remark=_("集群{}存在数据不一致，自动创建的数据修复单据").format(cluster.name),
                details=ticket_details,
            )


# ----------------------------- 异步执行任务函数 ----------------------------------------
@shared_task
def _apply_ticket_task(ticket_id: int, func_name: str, params: dict):
    """执行异步任务函数体"""
    params = params or {}
    getattr(TicketTask(ticket_id=ticket_id), func_name)(**params)


def apply_ticket_task(ticket_id: int, func_name: str, params: dict = None, eta: datetime = None) -> AsyncResult:
    """执行异步任务"""
    if not eta:
        logger.info(_("任务{}立即执行").format(func_name))
        res = _apply_ticket_task.apply_async((ticket_id, func_name, params))
    else:
        logger.info(_("任务{}定时执行，定时触发时间:{}").format(func_name, eta))
        # 注意⚠️：需要手动将美国时间转化成对应当前服务器时区时间，在settings设置的时区只对周期任务生效
        eta = eta + (datetime.utcnow() - datetime.now())
        res = _apply_ticket_task.apply_async((ticket_id, func_name, params), eta=eta)

    return res


# ----------------------------- 定时执行任务函数 ----------------------------------------
@shared_task
def auto_retry_exclusive_inner_flow():
    TicketTask.retry_exclusive_inner_flow()


@shared_task
def auto_create_data_repair_ticket():
    TicketTask.auto_create_data_repair_ticket()
