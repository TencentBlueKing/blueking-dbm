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
from typing import Any, Dict, List, Union

from celery import shared_task
from celery.result import AsyncResult
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _

from backend import env
from backend.components import BKLogApi
from backend.configuration.constants import PLAT_BIZ_ID, DBType
from backend.constants import DEFAULT_SYSTEM_USER
from backend.core import notify
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.ticket.builders.common.constants import MYSQL_CHECKSUM_TABLE, MySQLDataRepairTriggerMode
from backend.ticket.constants import (
    TICKET_EXPIRE_DEFAULT_CONFIG,
    TODO_RUNNING_STATUS,
    FlowErrCode,
    FlowType,
    FlowTypeConfig,
    TicketExpireType,
    TicketFlowStatus,
    TicketType,
    TodoType,
)
from backend.ticket.exceptions import TicketTaskTriggerException
from backend.ticket.models.ticket import Flow, Ticket, TicketFlowsConfig
from backend.utils.time import date2str, datetime2str

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
        from backend.ticket.flow_manager.inner import InnerFlow

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
    def auto_create_data_repair_ticket(cls):
        """根据例行校验的结果自动创建修复单据"""

        # 例行时间校验默认间隔一天
        now = datetime.now(timezone.utc).astimezone()
        start_time, end_time = now - timedelta(days=1), now
        # TODO: 目前这个esquery_search最多支持10000条查询，后续可以改造成scroll进行查询
        resp = BKLogApi.esquery_search(
            {
                "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.mysql_checksum_result",
                "start_time": datetime2str(start_time),
                "end_time": datetime2str(end_time),
                "query_string": "*",
                "start": 0,
                "size": 10000,
                "sort_list": [["dtEventTimeStamp", "asc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
            }
        )

        # 根据集群ID聚合日志
        cluster__checksum_logs_map: Dict[int, List[Dict]] = defaultdict(list)
        for hit in resp["hits"]["hits"]:
            checksum_log = json.loads(hit["_source"]["log"])
            cluster__checksum_logs_map[checksum_log["cluster_id"]].append(checksum_log)

        cluster_map = {c.id: c for c in Cluster.objects.filter(id__in=list(cluster__checksum_logs_map.keys()))}
        biz__db_type__repair_infos: Dict[int, Dict[DBType, List]] = defaultdict(lambda: defaultdict(list))

        # 为每个待修复的集群生成修复单据
        for cluster_id, checksum_logs in cluster__checksum_logs_map.items():
            # 忽略不在dbm meta信息中的集群
            if cluster_id not in cluster_map:
                logger.error(_("无法在dbm meta中查询到集群{}的相关信息，请排查该集群的状态".format(cluster_id)))
                continue

            cluster = cluster_map[cluster_id]

            # 根据logs获取ip:port和实例的映射
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

            # 获取修复单据详情信息
            ticket_infos = [
                {"cluster_id": cluster_id, "master": data_info["master"], "slaves": data_info["slaves"]}
                for data_info in data_repair_infos
            ]
            db_type = ClusterType.cluster_type_to_db_type(cluster.cluster_type)
            biz__db_type__repair_infos[cluster.bk_biz_id][db_type].extend(ticket_infos)

        # 构造修复单据
        for biz, db_type__repair_infos in biz__db_type__repair_infos.items():
            for db_type, repair_infos in db_type__repair_infos.items():
                ticket_details = {
                    # "非innodb表是否修复"这个参数与校验保持一致，默认为false
                    "is_sync_non_innodb": False,
                    "is_ticket_consistent": False,
                    "checksum_table": MYSQL_CHECKSUM_TABLE,
                    "trigger_type": MySQLDataRepairTriggerMode.ROUTINE.value,
                    "start_time": date2str(start_time),
                    "end_time": date2str(end_time),
                    "infos": [
                        {
                            "cluster_id": data_info["cluster_id"],
                            "master": data_info["master"],
                            "slaves": data_info["slaves"],
                        }
                        for data_info in repair_infos
                    ],
                }
                ticket_type = getattr(TicketType, f"{db_type.upper()}_DATA_REPAIR")
                _create_ticket.apply_async(
                    kwargs={
                        "ticket_type": ticket_type,
                        "creator": DEFAULT_SYSTEM_USER,
                        "bk_biz_id": biz,
                        "remark": _("集群存在数据不一致，自动创建的数据修复单据"),
                        "details": ticket_details,
                    }
                )

    @classmethod
    def auto_clear_expire_flow(cls):
        """清理过期的单据和flow，避免重试带来问题"""
        from backend.ticket.handler import TicketHandler
        from backend.ticket.models import Todo

        # 一次批量只操作100个单据
        batch = 100
        now = datetime.now(timezone.utc)
        # 只考虑平台级别的过期配置，暂不考虑业务和集群粒度
        ticket_configs = TicketFlowsConfig.objects.filter(bk_biz_id=PLAT_BIZ_ID)

        def filter_tickets(filters, expire_type):
            ticket_ids = []
            # itsm: 审批中的流程
            if expire_type == TicketExpireType.ITSM:
                filters &= Q(flow_type=FlowType.BK_ITSM, status=TicketFlowStatus.RUNNING)
                ticket_ids = list(Flow.objects.filter(filters).values_list("ticket", flat=True))
            # inner flow / pipeline: 失败的流程和pipeline暂停节点(防止重试)
            elif expire_type == TicketExpireType.INNER_FLOW:
                f = filters & Q(flow_type=FlowType.INNER_FLOW, status=TicketFlowStatus.FAILED)
                ticket_ids = list(Flow.objects.filter(f).values_list("ticket", flat=True))
                f = filters & Q(type=TodoType.INNER_APPROVE, status__in=TODO_RUNNING_STATUS)
                ticket_ids.extend(list(Todo.objects.filter(f).values_list("ticket", flat=True)))
            # flow-pause: 流程中的暂定节点
            elif expire_type == TicketExpireType.FLOW_TODO:
                filters &= Q(type__in=[TodoType.APPROVE, TodoType.RESOURCE_REPLENISH], status__in=TODO_RUNNING_STATUS)
                ticket_ids = list(Todo.objects.filter(filters).values_list("ticket", flat=True))

            return ticket_ids

        def get_expire_flow_tickets(expire_type):
            """获取超时过期的单据"""
            qs = []
            for cnf in ticket_configs:
                expire = cnf.configs.get(FlowTypeConfig.EXPIRE_CONFIG, TICKET_EXPIRE_DEFAULT_CONFIG)[expire_type]
                # -1表示无限制，不参与终止
                if expire < 0:
                    continue
                qs.append(Q(update_at__lt=now - timedelta(days=expire), ticket__ticket_type=cnf.ticket_type))

            # 如果设置为无限制过期，则不进行过滤
            if not qs:
                return []

            ticket_ids = filter_tickets(reduce(operator.or_, qs), expire_type)
            return ticket_ids

        def remind_expire_tickets(expire_type):
            """获取即将超时需要提醒的单据"""
            deadline_hours = [3, 72]
            for hour in deadline_hours:
                qs = []
                for cnf in ticket_configs:
                    expire = cnf.configs.get(FlowTypeConfig.EXPIRE_CONFIG, TICKET_EXPIRE_DEFAULT_CONFIG)[expire_type]
                    # -1表示无限制，不参与提醒
                    if expire < 0:
                        continue
                    # 超时提醒的区间是1小时，左闭右开，
                    # 即 terminate - hour - 1 <= now < terminate - hour; terminate = update_at + expire_days
                    st = now - timedelta(days=expire) + timedelta(hours=hour)
                    ed = now - timedelta(days=expire) + timedelta(hours=hour + 1)
                    qs.append(Q(update_at__gte=st, update_at__lt=ed, ticket__ticket_type=cnf.ticket_type))

                if not qs:
                    continue

                ticket_ids = filter_tickets(reduce(operator.or_, qs), expire_type)
                for ticket_id in ticket_ids:
                    notify.send_msg.apply_async(
                        args=(
                            ticket_id,
                            hour,
                        )
                    )

        # 根据超时保护类型，获取需要过期处理的单据
        expire_ticket_ids = []
        for expire_type in TicketExpireType.get_values():
            expire_ticket_ids.extend(get_expire_flow_tickets(expire_type))
            remind_expire_tickets(expire_type)

        # 终止单据
        TicketHandler.revoke_ticket(ticket_ids=expire_ticket_ids[:batch], operator=DEFAULT_SYSTEM_USER)


# ----------------------------- 异步执行任务函数 ----------------------------------------
@shared_task
def _create_ticket(ticket_type, creator, bk_biz_id, remark, details) -> None:
    """创建一个新单据"""
    Ticket.create_ticket(ticket_type=ticket_type, creator=creator, bk_biz_id=bk_biz_id, remark=remark, details=details)


@shared_task
def _apply_ticket_task(ticket_id: int, func_name: str, params: dict):
    """执行异步任务函数体"""
    params = params or {}
    getattr(TicketTask(ticket_id=ticket_id), func_name)(**params)


def apply_ticket_task(
    ticket_id: int, func_name: str, params: dict = None, eta: Union[int, datetime] = None
) -> AsyncResult:
    """执行异步任务"""
    if not eta:
        logger.info(_("任务{}立即执行").format(func_name))
        res = _apply_ticket_task.apply_async((ticket_id, func_name, params))
    else:
        logger.info(_("任务{}定时执行，定时触发时间:{}").format(func_name, eta))
        if isinstance(eta, datetime):
            # 注意⚠️：如果传入的是无时区datetime，需要手动将美国时间转化成对应当前服务器时区时间，在settings设置的时区只对周期任务生效
            # eta = eta + (datetime.utcnow() - datetime.now())
            res = _apply_ticket_task.apply_async((ticket_id, func_name, params), eta=eta)
        elif isinstance(eta, int):
            res = _apply_ticket_task.apply_async((ticket_id, func_name, params), countdown=eta)
        else:
            raise TicketTaskTriggerException(_("不支持的定时类型: {}").format(eta))

    return res
