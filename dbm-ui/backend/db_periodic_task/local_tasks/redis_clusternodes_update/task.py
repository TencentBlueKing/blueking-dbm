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
import datetime
import json
import logging
import traceback
from collections import defaultdict
from typing import Dict, List

from celery.schedules import crontab
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _

from backend import env
from backend.components.bklog.client import BKLogApi
from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta.enums import InstanceInnerRole, InstanceRole, InstanceStatus
from backend.db_meta.models import Cluster, StorageInstance, StorageInstanceTuple
from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.db_services.redis.autofix.enums import AutofixStatus
from backend.db_services.redis.autofix.models import (
    NodeUpdateTaskStatus,
    RedisAutofixCore,
    TbRedisClusterNodesUpdateTask,
)
from backend.flow.consts import RedisRole
from backend.flow.utils.redis.redis_cluster_nodes import ClusterNodeData, decode_cluster_nodes
from backend.flow.utils.redis.redis_module_operate import RedisCCTopoOperator
from backend.ticket.constants import TicketType
from backend.ticket.models.ticket import ClusterOperateRecord
from backend.utils.string import pascal_to_snake
from backend.utils.time import strptime

logger = logging.getLogger("celery")


# 获取最近N分钟的redis cluster nodes上报日志
def last_Nmin_clusternodes_report(minute: int = 2):
    # 时间格式 2021-03-18 10:00:00
    start_time = (
        datetime.datetime.now() - datetime.timedelta(minutes=minute) + datetime.timedelta(seconds=1)
    ).strftime("%Y-%m-%d %H:%M:%S")
    end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(
        "last_Nmin_redis_clusternodes_update_report ==>start_time: {}, end_time: {}".format(start_time, end_time)
    )
    collector = "redis_cluster_nodes_result"
    resp = BKLogApi.esquery_search(
        {
            "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.{collector}",
            "start_time": start_time,
            "end_time": end_time,
            # 这里需要精确查询集群域名，所以可以通过log: "key: \"value\""的格式查询
            "query_string": "*",
            "start": 0,
            "size": 6000,
            "sort_list": [["dtEventTimeStamp", "asc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
        },
        use_admin=True,
    )
    backup_logs = []
    for hit in resp["hits"]["hits"]:
        raw_log = json.loads(hit["_source"]["log"])
        backup_logs.append({pascal_to_snake(key): value for key, value in raw_log.items()})

    return backup_logs


# 根据 immute_domain 聚合保存到 map[string]struct{}中,相同 immute_domain 根据update_at保留最新的一条数据
def redis_cluster_nodes_group_by_domain(nodes_records: list):
    domain_latest_nodes = {}
    for record in nodes_records:
        immute_domain = record["immute_domain"]
        update_at = record["update_at"]
        if immute_domain not in domain_latest_nodes:
            domain_latest_nodes[immute_domain] = record
        else:
            if update_at > domain_latest_nodes[immute_domain]["update_at"]:
                domain_latest_nodes[immute_domain] = record
    return domain_latest_nodes


@register_periodic_task(run_every=crontab(minute="*/2"))
def redis_clusternodes_update_record():
    """
    保存"redis cluster nodes更新"记录
    """
    reports = last_Nmin_clusternodes_report(minute=2)
    if len(reports) == 0:
        return
    domain_latest_nodes = redis_cluster_nodes_group_by_domain(reports)
    for domain, nodes_data in domain_latest_nodes.items():
        row = TbRedisClusterNodesUpdateTask.objects.create(
            bk_biz_id=nodes_data["bk_biz_id"],
            immute_domain=nodes_data["immute_domain"],
            report_server_ip=nodes_data["server_ip"],
            report_server_port=nodes_data["server_port"],
            report_nodes_data=nodes_data["nodes_data"],
            report_time=strptime(nodes_data["update_at"]),
            status=NodeUpdateTaskStatus.TODO.value,
        )
        cluster = Cluster.objects.get(
            immute_domain=nodes_data["immute_domain"], bk_biz_id=int(nodes_data["bk_biz_id"])
        )
        if not cluster:
            # 根据上报的immute_domain找不到对应的集群,记做失败
            row.status = NodeUpdateTaskStatus.FAILED.value
            row.message = _("根据上报的immute_domain找不到对应的集群")
            row.save()
            continue
        row.cluster_id = cluster.id
        row.cluster_type = cluster.cluster_type
        # 判断是否有节点变更类型的单据正在执行,如果有,不做处理
        opers = ClusterOperateRecord.objects.get_cluster_operations(cluster_id=cluster.id)
        oper_title = ""
        oper_type = ""
        for oper in opers:
            if oper["ticket_type"] and oper["ticket_type"] in [
                TicketType.REDIS_SCALE_UPDOWN.value,
                TicketType.REDIS_CLUSTER_CUTOFF.value,
                TicketType.REDIS_CLUSTER_INSTANCE_SHUTDOWN.value,
                TicketType.REDIS_MASTER_SLAVE_SWITCH.value,
                TicketType.REDIS_CLUSTER_ADD_SLAVE.value,
                TicketType.REDIS_CLUSTER_VERSION_UPDATE_ONLINE.value,
            ]:
                oper_title = oper["title"]
                oper_type = oper["ticket_type"]
                break
        if oper_type:
            row.status = NodeUpdateTaskStatus.CANCELED.value
            row.message = _("集群:{} 存在'{}({})'的单据正在执行").format(domain, oper_title, oper_type)
            row.save()
            continue
        # 记录为待执行
        row.status = NodeUpdateTaskStatus.TODO.value
        row.message = _("待执行")
        row.save()


@register_periodic_task(run_every=crontab(minute="*/2"))
def redis_clusternodes_update_deal():
    """
    处理'redis cluster nodes更新'
    """
    # 获取待处理的记录
    rows = TbRedisClusterNodesUpdateTask.objects.filter(
        status=NodeUpdateTaskStatus.TODO.value,
        create_time__gte=datetime.datetime.now(timezone.utc) - datetime.timedelta(hours=2),
    )
    for row in rows:
        # 根据上报的immute_domain找到对应的集群
        cluster = Cluster.objects.get(immute_domain=row.immute_domain, bk_biz_id=row.bk_biz_id)
        if not cluster:
            # 根据上报的immute_domain找不到对应的集群,记做失败
            row.status = NodeUpdateTaskStatus.FAILED.value
            row.message = _("根据上报的immute_domain找不到对应的集群")
            row.save()
            continue
        job = RedisClusterNodesUpdateJob(
            task_record=row,
        )
        # 根据上报的nodes_data更新meta中的节点状态
        job.deal_nodes_update_event()


class RedisClusterNodesUpdateJob:
    """
    一个 cluster 的nodes更新任务
    """

    def __init__(self, task_record: TbRedisClusterNodesUpdateTask):
        self.addr_to_cluster_node: Dict[str, ClusterNodeData] = None
        self.nodeid_to_cluster_node: Dict[str, ClusterNodeData] = None
        self.task_row: TbRedisClusterNodesUpdateTask = task_record
        self.detail_msg = ""
        self.role_updated_instances: List[Dict] = []

    def decode_raw_nodes_data(self):
        _, self.addr_to_cluster_node = decode_cluster_nodes(self.task_row.report_nodes_data)
        self.nodeid_to_cluster_node = {node.node_id: node for node in self.addr_to_cluster_node.values()}

    def update_node_status(self, meta_obj: StorageInstance, cluster_node: ClusterNodeData):
        """
        更新节点状态
        """
        if meta_obj.status == InstanceStatus.RUNNING.value and cluster_node.is_running():
            # 节点状态没变
            return
        if meta_obj.status == InstanceStatus.UNAVAILABLE.value and (not cluster_node.is_running()):
            # 节点状态没变
            return
        if meta_obj.status == InstanceStatus.RUNNING.value and (not cluster_node.is_running()):
            # 节点状态变成了不可用
            self.detail_msg += _("{}:{} 状态变成了不可用\n").format(meta_obj.instance_inner_role, meta_obj.ip_port)
            meta_obj.status = InstanceStatus.UNAVAILABLE.value
        if meta_obj.status == InstanceStatus.UNAVAILABLE.value and cluster_node.is_running():
            # 节点状态变成了可用
            self.detail_msg += _("{}:{} 状态变成了可用\n").format(meta_obj.instance_inner_role, meta_obj.ip_port)
            meta_obj.status = InstanceStatus.RUNNING.value
        meta_obj.save(update_fields=["status"])

    def deal_slave_node_update(
        self, slave_node: ClusterNodeData = None, master_obj: StorageInstance = None, slave_obj: StorageInstance = None
    ):
        if slave_node and slave_node.get_role() == RedisRole.MASTER.value and slave_node.is_running():
            # meta中的slave实际已经变成了master角色,且是running状态
            # (为何必须是running状态,因为在处理 非running的master时?
            # deal_master_node_update函数会将 非running master 变成 slave,进而发起自愈
            # 所以如果不指定running 状态的master,就会出现 deal_master_node_update()将节点变成 slave,
            # 而后  deal_slave_node_update()将slave变成master 的情况)

            # 建立proxy和slave的关系
            tmp_proxy_objs = list(master_obj.proxyinstance_set.all())
            slave_obj.proxyinstance_set.add(*tmp_proxy_objs)
            # 删除meta中旧的master和slave的关系
            if StorageInstanceTuple.objects.filter(ejector=master_obj, receiver=slave_obj).exists():
                StorageInstanceTuple.objects.get(ejector=master_obj, receiver=slave_obj).delete(keep_parents=True)
            # 更新meta中slave的role为master
            slave_obj.instance_role = InstanceRole.REDIS_MASTER.value
            slave_obj.instance_inner_role = InstanceInnerRole.MASTER.value
            self.detail_msg += _("slave:{} 变成了master\n").format(slave_obj.ip_port)
            slave_obj.save(update_fields=["instance_role", "instance_inner_role"])
            self.role_updated_instances.append({"ip": slave_node.ip, "port": slave_node.port})
        if slave_node:
            # 根据cluster nodes中实际status,更新meta中slave的状态
            self.update_node_status(slave_obj, slave_node)

    def deal_master_node_update(
        self,
        cluster: Cluster,
        master_node: ClusterNodeData = None,
        slave_node: ClusterNodeData = None,
        master_obj: StorageInstance = None,
        slave_obj: StorageInstance = None,
    ):
        if master_node and master_node.get_role() == RedisRole.SLAVE.value:
            # meta中的master节点实际已经变成了slave角色
            # old master清理和proxy的关系
            master_obj.proxyinstance_set.clear()
            # 更新meta中old master的role为slave
            self.detail_msg += _("master:{} 变成了slave\n").format(master_obj.ip_port)
            master_obj.instance_role = InstanceRole.REDIS_SLAVE.value
            master_obj.instance_inner_role = InstanceInnerRole.SLAVE.value
            master_obj.save(update_fields=["instance_role", "instance_inner_role"])
            # 根据 masterid找到 new master node
            new_master_node = self.nodeid_to_cluster_node.get(master_node.master_id, None)
            if not new_master_node:
                return
            new_master_obj = cluster.storageinstance_set.get(machine__ip=new_master_node.ip, port=new_master_node.port)
            if not new_master_obj:
                # 如果new master并不在cluster中元数据中,不做处理
                self.detail_msg += _("master:{} 变成了slave,但是其master({}:{})不在集群meta数据中,所以不做处理\n").format(
                    master_obj.ip_port, new_master_node.ip, new_master_node.port
                )
                return
            new_slave_obj = master_obj
            # 建立 new_master 和 new_slave(old_master) 的关系
            StorageInstanceTuple.objects.create(ejector=new_master_obj, receiver=new_slave_obj)
            self.role_updated_instances.append({"ip": master_node.ip, "port": master_node.port})
        elif (
            master_node
            and master_node.get_role() == RedisRole.MASTER.value
            and (not master_node.is_running())
            and slave_node
            and slave_node.is_running()
            and slave_node.get_role() == RedisRole.MASTER.value
            and len(slave_node.slots) > 0
        ):
            # meta中的master节点实际还是master角色,但是状态异常,且他原本的slave节点成了master角色并负责slots
            # 那么说明发生了 master 故障且没有拉起来的情况
            # 此时我们将meta中这个unrunning master变成 new master(old slave)的 slave
            # 后面如果 unrunning master所在机器所有实例都变成 unrunning了,说明机器发生了故障,后续可以发起自愈流程

            # old master清理和proxy的关系
            master_obj.proxyinstance_set.clear()
            # 更新meta中old master的role为slave
            self.detail_msg += _(
                "master:{} 变成了disconnected状态,其slave:{}变成了master,现将old_master变成其slave,便于发起自愈\n"
            ).format(master_obj.ip_port, slave_obj.ip_port)
            master_obj.instance_role = InstanceRole.REDIS_SLAVE.value
            master_obj.instance_inner_role = InstanceInnerRole.SLAVE.value
            master_obj.save(update_fields=["instance_role", "instance_inner_role"])
            # 删除meta中旧的master->slave的关系
            if StorageInstanceTuple.objects.filter(ejector=master_obj, receiver=slave_obj).exists():
                StorageInstanceTuple.objects.get(ejector=master_obj, receiver=slave_obj).delete(keep_parents=True)
            # 建立新的 new_master(old_slave) -> unrunning master 的关系
            new_master_obj = slave_obj
            new_slave_obj = master_obj
            StorageInstanceTuple.objects.create(ejector=new_master_obj, receiver=new_slave_obj)
            self.role_updated_instances.append({"ip": master_node.ip, "port": master_node.port})
        if master_node:
            # 根据cluster nodes中实际status,更新meta中master的状态
            self.update_node_status(master_obj, master_node)

    def is_repl_pair_still_ok(
        self,
        master_node: ClusterNodeData = None,
        slave_node: ClusterNodeData = None,
        master_obj: StorageInstance = None,
        slave_obj: StorageInstance = None,
    ) -> bool:
        """
        是否master依然是running master,slave依然是running slave,主从关系也没变
        """
        if (
            master_node
            and slave_node
            and master_node.get_role() == RedisRole.MASTER.value
            and master_node.is_running()
            and slave_node.get_role() == RedisRole.SLAVE.value
            and slave_node.is_running()
            and slave_node.master_id == master_node.node_id
            and master_obj.status == InstanceStatus.RUNNING.value
            and slave_obj.status == InstanceStatus.RUNNING.value
        ):
            return True
        return False

    # 修改cc 信息
    def update_cc_info(self, cluster: Cluster):
        if len(self.role_updated_instances) == 0:
            return
        where = Q()
        for item in self.role_updated_instances:
            where |= Q(machine__ip=item["ip"], port=item["port"])
        role_updated_insts = StorageInstance.objects.filter(where)
        RedisCCTopoOperator(cluster).transfer_instances_to_cluster_module(role_updated_insts)

    # 发起自愈流程
    def start_autofix_flow(self, cluster: Cluster):
        # 如果存在集群中某个slave机器,所有实例均变成了 unrunning 状态,则对其发起自愈流程
        slave_group_by_ip = defaultdict(list)
        for slave_obj in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_SLAVE.value):
            slave_group_by_ip[slave_obj.machine.ip].append(slave_obj)
        fault_machines = []
        for ip, slave_objs in slave_group_by_ip.items():
            if all([slave_obj.status == InstanceStatus.UNAVAILABLE.value for slave_obj in slave_objs]):
                # 该机器所有实例都unrunning了
                # 继续检测该机器 10 分钟内没被加入到自愈流程中
                mins10_ago = datetime.datetime.now() - datetime.timedelta(minutes=10)
                rows = RedisAutofixCore.objects.filter(cluster_id=cluster.id, create_at__gt=mins10_ago)
                exists = False
                for row in rows:
                    if ip in [item["ip"] for item in json.loads(row.fault_machines)]:
                        exists = True
                        break
                if not exists:
                    fault_machines.append({"instance_type": slave_objs[0].machine_type, "ip": ip})
        if len(fault_machines) > 0:
            unavail_ips = [item["ip"] for item in fault_machines]
            self.detail_msg += _("存在机器:{} 所有实例均变成了unrunning状态,发起自愈流程\n").format(unavail_ips)
            RedisAutofixCore.objects.create(
                bk_biz_id=cluster.bk_biz_id,
                bk_cloud_id=cluster.bk_cloud_id,
                cluster_id=cluster.id,
                immute_domain=cluster.immute_domain,
                cluster_type=cluster.cluster_type,
                fault_machines=json.dumps(fault_machines),
                deal_status=AutofixStatus.AF_TICKET.value,
                status_version=get_random_string(length=12),
            ).save()

    def deal_nodes_update_event(self):
        """
        根据cluster nodes信息调整db_meta中数据;
        扩缩容时新安装的node通过cluster meet加入集群,通过cluster nodes上报,但是这些node的meta会通过自身flow去更新.
        所以对于存在于cluster nodes中但是不在集群本身的元数据中的节点,不做处理.
        """
        try:
            with transaction.atomic():
                self.task_row.status = NodeUpdateTaskStatus.DOING.value
                self.task_row.message = _("开始更新集群:{} 元数据").format(self.task_row.immute_domain)
                self.task_row.save(update_fields=["status", "message"])
                self.decode_raw_nodes_data()
                cluster = Cluster.objects.get(
                    immute_domain=self.task_row.immute_domain, bk_biz_id=self.task_row.bk_biz_id
                )
                for master_obj in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
                    if master_obj.as_ejector and master_obj.as_ejector.first():
                        slave_obj = master_obj.as_ejector.get().receiver
                        meta_master_addr = master_obj.ip_port
                        meta_slave_addr = slave_obj.ip_port
                        master_node = self.addr_to_cluster_node.get(meta_master_addr, None)
                        slave_node = self.addr_to_cluster_node.get(meta_slave_addr, None)
                        if self.is_repl_pair_still_ok(master_node, slave_node, master_obj, slave_obj):
                            # 主从状态和关系都没变
                            self.detail_msg += _("master:{} 和 slave:{} 主从状态和关系都没变,不做处理\n").format(
                                meta_master_addr, meta_slave_addr
                            )
                            continue
                        self.deal_slave_node_update(slave_node, master_obj, slave_obj)
                        self.deal_master_node_update(cluster, master_node, slave_node, master_obj, slave_obj)
                    else:
                        # meta中该master没有slave
                        meta_master_addr = master_obj.ip_port
                        master_node = self.addr_to_cluster_node.get(meta_master_addr, None)
                        self.deal_master_node_update(cluster, master_node, None, master_obj, None)
                # 转移cc模块
                self.update_cc_info(cluster)
                # 尝试发起自愈
                self.start_autofix_flow(cluster)
        except Exception as e:
            logger.error(traceback.format_exc())
            self.task_row.status = NodeUpdateTaskStatus.FAILED.value
            self.task_row.message = _("处理异常,{}").format(e)
            self.task_row.save(update_fields=["status", "message"])
            return
        self.task_row.status = NodeUpdateTaskStatus.SUCCESS.value
        self.task_row.message = self.detail_msg
        self.task_row.save(update_fields=["status", "message"])
