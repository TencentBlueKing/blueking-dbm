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
import base64
import copy
import logging
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.db.transaction import atomic
from django.utils.translation import ugettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.configuration.handlers.dba import DBAdministratorHandler
from backend.db_meta import api
from backend.db_meta.api.cluster.nosqlcomm.create_cluster import update_cluster_type
from backend.db_meta.api.cluster.rediscluster.handler import RedisClusterHandler
from backend.db_meta.api.cluster.tendiscache.handler import TendisCacheClusterHandler
from backend.db_meta.api.cluster.tendispluscluster.handler import TendisPlusClusterHandler
from backend.db_meta.api.cluster.tendissingle.handler import TendisSingleHandler
from backend.db_meta.api.cluster.tendisssd.handler import TendisSSDClusterHandler
from backend.db_meta.enums import (
    AccessLayer,
    ClusterEntryRole,
    ClusterEntryType,
    ClusterPhase,
    ClusterType,
    InstanceInnerRole,
    InstanceRole,
    MachineType,
)
from backend.db_meta.models import (
    CLBEntryDetail,
    Cluster,
    ClusterEntry,
    Machine,
    PolarisEntryDetail,
    ProxyInstance,
    StorageInstance,
    StorageInstanceTuple,
)
from backend.db_services.dbbase.constants import IP_PORT_DIVIDER, SPACE_DIVIDER
from backend.db_services.redis.rollback.models import TbTendisRollbackTasks
from backend.db_services.redis.slots_migrate.models import TbTendisSlotsMigrateRecord
from backend.db_services.redis.util import (
    is_redis_cluster_protocal,
    is_redis_instance_type,
    is_tendisplus_instance_type,
    is_tendisssd_instance_type,
)
from backend.flow.consts import DEFAULT_DB_MODULE_ID, DEFAULT_REDIS_START_PORT, InstanceStatus
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.cc_manage import CcManage
from backend.flow.utils.dns_manage import DnsManage
from backend.flow.utils.redis.redis_module_operate import RedisCCTopoOperator
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class RedisDBMeta(object):
    """
    根据单据信息和集群信息，更新cmdb
    类的方法一定以单据类型的小写进行命名，否则不能根据单据类型匹配对应的方法
    """

    def __init__(self, ticket_data: dict, cluster: dict):
        """
        @param ticket_data : 单据信息
        @param cluster: 集群信息
        """
        self.ticket_data = ticket_data
        self.cluster = cluster

    def write(self) -> bool:
        function_name = self.cluster["meta_func_name"].lower()
        if hasattr(self, function_name):
            return getattr(self, function_name)()

        logger.error(_("找不到单据类型需要变更的cmdb函数，请联系系统管理员"))
        return False

    def read(self) -> (dict, bool):
        function_name = self.cluster["meta_func_name"].lower()
        if hasattr(self, function_name):
            return getattr(self, function_name)()

        logger.error(_("找不到单据类型需要查询的cmdb函数，请联系系统管理员"))

    def proxy_install(self) -> bool:
        """
        机器上架元数据写入,这里只是单纯的上架，不会加入集群
        """
        machines = []
        proxies = []
        machine_type = self.cluster["machine_type"]
        for ip in self.cluster["new_proxy_ips"]:
            machines.append(
                {
                    "bk_biz_id": self.cluster["bk_biz_id"],
                    "ip": ip,
                    "machine_type": machine_type,
                    "spec_id": self.cluster["spec_id"],
                    "spec_config": self.cluster["spec_config"],
                }
            )
            proxies.append({"ip": ip, "port": self.cluster["port"]})

        with atomic():
            ins_status = InstanceStatus.RUNNING
            if self.cluster.get("ins_status"):
                ins_status = self.cluster["ins_status"]
            api.machine.create(
                machines=machines, creator=self.cluster["created_by"], bk_cloud_id=self.cluster["bk_cloud_id"]
            )
            api.proxy_instance.create(proxies=proxies, creator=self.cluster["created_by"], status=ins_status)
        return True

    def proxy_add_cluster(self) -> bool:
        """
        proxy只做加入集群操作
        """
        proxies = []
        for ip in self.cluster["proxy_ips"]:
            proxies.append({"ip": ip, "port": self.cluster["proxy_port"]})
        cluster = Cluster.objects.get(immute_domain=self.cluster["domain_name"])
        with atomic():
            api.cluster.nosqlcomm.add_proxies(cluster, proxies=proxies)
        return True

    def proxy_del_cluster(self) -> bool:
        """
        proxy缩容，这里只是把proxy从集群中删除，不会清理machine和proxyins表的数据
        """
        proxies = []
        for ip in self.cluster["proxy_ips"]:
            proxies.append({"ip": ip, "port": self.cluster["proxy_port"]})
        cluster = Cluster.objects.get(immute_domain=self.cluster["domain_name"])
        api.cluster.nosqlcomm.delete_proxies(cluster, proxies=proxies)
        return True

    def proxy_uninstall(self) -> bool:
        """
        proxy下架，从集群中剔除，并清理machine和proxy表
        """
        proxies = []
        for ip in self.cluster["proxy_ips"]:
            proxies.append({"ip": ip, "port": self.cluster["proxy_port"]})
        cluster = Cluster.objects.get(immute_domain=self.cluster["domain_name"])
        api.cluster.nosqlcomm.decommission_proxies(cluster, proxies=proxies, is_all=False)
        return True

    # 统一的，暴力清理入口
    def clear_machines(self) -> bool:
        api.machine.clear_info_for_machine(machines=self.ticket_data["clear_hosts"])

    def clear_dirty_proxy_dbmetas(self) -> bool:
        """
        清理没在集群中的proxy的dbmeta
        """
        proxy_ip = self.cluster["proxy_ips"][0]
        bk_cloud_id = self.cluster["bk_cloud_id"]
        proxy_inst = ProxyInstance.objects.filter(machine__ip=proxy_ip, machine__bk_cloud_id=bk_cloud_id).first()
        cc_manage = CcManage(proxy_inst.bk_biz_id, proxy_inst.cluster_type)
        proxy_objs = ProxyInstance.objects.filter(machine__ip=proxy_ip)
        cc_manage.delete_service_instance(bk_instance_ids=[obj.bk_instance_id for obj in proxy_objs])
        for proxy_obj in proxy_objs:
            logger.info("proxy_instance:{}:{} storage delete".format(proxy_obj.machine.ip, proxy_obj.port))
            proxy_obj.storageinstance.clear()
            logger.info("proxy_instance:{}:{} cluster_bind_entry delete".format(proxy_obj.machine.ip, proxy_obj.port))
            proxy_obj.bind_entry.clear()
            logger.info("proxy_instance:{}:{} cluster_bind_entry delete".format(proxy_obj.machine.ip, proxy_obj.port))
            proxy_obj.delete()
            # 需要检查， 是否该机器上所有实例都已经清理干净，
            if ProxyInstance.objects.filter(machine__ip=proxy_obj.machine.ip, bk_biz_id=proxy_obj.bk_biz_id).exists():
                logger.info("ignore proxy machine {} , another instance existed.".format(proxy_obj.machine))
            else:
                logger.info("proxy machine {}".format(proxy_obj.machine))
                cc_manage.recycle_host([proxy_obj.machine.bk_host_id])
                proxy_obj.machine.delete()
        logger.info("{} proxy_instance delete".format(proxy_ip))
        return True

    def proxy_status_update(self) -> bool:
        """
        proxy状态更新
        """
        api.proxy_instance.update(
            proxies=[
                {
                    "ip": self.cluster["ip"],
                    "port": self.cluster["port"],
                    "status": (
                        InstanceStatus.RUNNING.value
                        if self.ticket_data["ticket_type"] == TicketType.REDIS_PROXY_OPEN
                        else InstanceStatus.UNAVAILABLE.value
                    ),
                }
            ]
        )
        return True

    def cluster_status_update(self) -> bool:
        cluster = Cluster.objects.get(id=self.cluster["cluster_id"])
        if (
            self.ticket_data["ticket_type"] == TicketType.REDIS_PROXY_CLOSE
            or self.ticket_data["ticket_type"] == TicketType.REDIS_INSTANCE_CLOSE
        ):
            cluster.phase = ClusterPhase.OFFLINE.value
        else:
            cluster.phase = ClusterPhase.ONLINE.value
        cluster.save()
        return True

    def redis_install_append(self) -> bool:
        """
        Redis单实例级别上架
        需要判断machine表是否已写入过
        {
            "cluster_type"
            "master_ip":xxx,
            "slave_ip":xxx,
            "ports": [],
            "spec_config",
            "spec_id"
        }
        """
        machines, ins = [], []
        for port in self.cluster["ports"]:
            ins.append(
                {"ip": self.cluster["master_ip"], "port": port, "instance_role": InstanceRole.REDIS_MASTER.value}
            )
            ins.append({"ip": self.cluster["slave_ip"], "port": port, "instance_role": InstanceRole.REDIS_SLAVE.value})

        ips = [self.cluster["master_ip"], self.cluster["slave_ip"]]
        m = Machine.objects.filter(ip__in=ips).values("ip")
        if len(m) != 2:
            if "cluster_type" in self.ticket_data:
                cluster_type = self.ticket_data["cluster_type"]
            else:
                cluster_type = self.cluster["cluster_type"]

            if is_redis_instance_type(cluster_type):
                machine_type = MachineType.TENDISCACHE.value
            elif is_tendisssd_instance_type(cluster_type):
                machine_type = MachineType.TENDISSSD.value
            elif is_tendisplus_instance_type(cluster_type):
                machine_type = MachineType.TENDISPLUS.value
            else:
                machine_type = ""

            machines.append(
                {
                    "bk_biz_id": self.ticket_data["bk_biz_id"],
                    "ip": self.cluster["master_ip"],
                    "machine_type": machine_type,
                    "spec_id": self.cluster["spec_id"],
                    "spec_config": self.cluster["spec_config"],
                }
            )
            machines.append(
                {
                    "bk_biz_id": self.ticket_data["bk_biz_id"],
                    "ip": self.cluster["slave_ip"],
                    "machine_type": machine_type,
                    "spec_id": self.cluster["spec_id"],
                    "spec_config": self.cluster["spec_config"],
                }
            )
        with atomic():
            ins_status = InstanceStatus.RUNNING
            if self.cluster.get("ins_status"):
                ins_status = self.cluster["ins_status"]
            if "bk_cloud_id" in self.ticket_data:
                bk_cloud_id = self.ticket_data["bk_cloud_id"]
            else:
                bk_cloud_id = self.cluster["bk_cloud_id"]
            if len(machines) != 0:
                api.machine.create(machines=machines, creator=self.ticket_data["created_by"], bk_cloud_id=bk_cloud_id)
            api.storage_instance.create(instances=ins, creator=self.ticket_data["created_by"], status=ins_status)
        return True

    def redis_install(self) -> bool:
        """
        Redis实例上架、单机器级别。
        """
        bk_cloud_id, ins_status = 0, InstanceStatus.RUNNING
        if self.cluster.get("ins_status"):
            ins_status = self.cluster["ins_status"]
        if "bk_cloud_id" in self.ticket_data:
            bk_cloud_id = self.ticket_data["bk_cloud_id"]
        else:
            bk_cloud_id = self.cluster["bk_cloud_id"]

        machines, ins, cluster_type = [], [], ""
        if "cluster_type" in self.ticket_data:
            cluster_type = self.ticket_data["cluster_type"]
        else:
            cluster_type = self.cluster["cluster_type"]

        if is_redis_instance_type(cluster_type):
            machine_type = MachineType.TENDISCACHE.value
        elif is_tendisssd_instance_type(cluster_type):
            machine_type = MachineType.TENDISSSD.value
        elif is_tendisplus_instance_type(cluster_type):
            machine_type = MachineType.TENDISPLUS.value
        else:
            machine_type = ""

        if self.cluster.get("new_master_ips"):
            for ip in self.cluster.get("new_master_ips"):
                machines.append(
                    {
                        "bk_biz_id": self.ticket_data["bk_biz_id"],
                        "ip": ip,
                        "machine_type": machine_type,
                        "spec_id": self.cluster["spec_id"],
                        "spec_config": self.cluster["spec_config"],
                    }
                )
                if self.cluster.get("inst_num"):
                    for n in range(0, self.cluster["inst_num"]):
                        port = n + self.cluster["start_port"]
                        ins.append({"ip": ip, "port": port, "instance_role": InstanceRole.REDIS_MASTER.value})
                elif self.cluster.get("ports"):
                    for port in self.cluster["ports"]:
                        ins.append({"ip": ip, "port": port, "instance_role": InstanceRole.REDIS_MASTER.value})

        if self.cluster.get("new_slave_ips"):
            for ip in self.cluster.get("new_slave_ips"):
                machines.append(
                    {
                        "bk_biz_id": self.ticket_data["bk_biz_id"],
                        "ip": ip,
                        "machine_type": machine_type,
                        "spec_id": self.cluster["spec_id"],
                        "spec_config": self.cluster["spec_config"],
                    }
                )
                if self.cluster.get("inst_num"):
                    for n in range(0, self.cluster["inst_num"]):
                        port = n + self.cluster["start_port"]
                        ins.append({"ip": ip, "port": port, "instance_role": InstanceRole.REDIS_SLAVE.value})
                elif self.cluster.get("ports"):
                    for port in self.cluster["ports"]:
                        ins.append({"ip": ip, "port": port, "instance_role": InstanceRole.REDIS_SLAVE.value})

        with atomic():
            if cluster_type == ClusterType.TendisRedisInstance.value:
                api.machine.get_or_create(
                    machines=machines, creator=self.ticket_data["created_by"], bk_cloud_id=bk_cloud_id
                )
            else:
                api.machine.create(machines=machines, creator=self.ticket_data["created_by"], bk_cloud_id=bk_cloud_id)
            api.storage_instance.create(instances=ins, creator=self.ticket_data["created_by"], status=ins_status)
        return True

    def redisinstance_install_for_diff_config(self) -> bool:
        """
        redis主从集群存在不同配置(如密码,databases)
        insts: [
            {"ip":xxx,"port":xxx,"instance_role":"redis_slave"},
        ]
        machines: [
            {"bk_biz_id":xxx,"ip":xxx,"machine_type":xxx,"spec_id":xxx,"spec_config":xxx},
        ]
        """
        bk_cloud_id = self.cluster.get("bk_cloud_id")
        insts = self.cluster.get("insts")
        machines = self.cluster.get("machines")
        api.machine.get_or_create(machines=machines, creator=self.ticket_data["created_by"], bk_cloud_id=bk_cloud_id)
        api.storage_instance.create(
            instances=insts, creator=self.ticket_data["created_by"], status=InstanceStatus.RUNNING
        )

    def replicaof_ins(self) -> bool:
        """
        单实例上架主从关系
        "bacth_pairs": [
            {
                "master_ip":xxx,
                "master_port":xxx,
                "slave_ip":xxx,
                "slave_port":xxx,
            }
        ]
        """
        replic_tuple = []
        for pair in self.cluster["bacth_pairs"]:
            replic_tuple.append(
                {
                    "ejector": {
                        "ip": pair["master_ip"],
                        "port": pair["master_port"],
                    },
                    "receiver": {
                        "ip": pair["slave_ip"],
                        "port": pair["slave_port"],
                    },
                }
            )
        api.storage_instance_tuple.create(replic_tuple, creator=self.cluster["created_by"])
        return True

    def replicaof(self) -> bool:
        """
        批量配置主从关系,传参为cluster。 主要是在安装时使用
        "inst_num":xx,
        "start_port":xx,
        "bacth_pairs": [
            {
                "master_ip":xxx,
                "slave_ip":xxx,
            }
        ]
        """
        replic_tuple = []
        for pair in self.cluster["bacth_pairs"]:
            master_ip = pair["master_ip"]
            slave_ip = pair["slave_ip"]
            master_start_port = self.cluster["start_port"]
            slave_start_port = self.cluster["start_port"]
            inst_num = self.cluster["inst_num"]

            for n in range(0, inst_num):
                replic_tuple.append(
                    {
                        "ejector": {
                            "ip": master_ip,
                            "port": master_start_port + n,
                        },
                        "receiver": {
                            "ip": slave_ip,
                            "port": slave_start_port + n,
                        },
                    }
                )
        api.storage_instance_tuple.create(replic_tuple, creator=self.cluster["created_by"])
        return True

    def replicaof_link(self) -> bool:
        """
        批量配置主从关系。传参为实例对应关系列表
        [
            {
                "master_ip":xxx,
                "master_port:xx,
                "slave_ip":xxx,
                "slave_port":xx
            }
        ]
        """
        replic_tuple = []
        for repl_info in self.cluster["repl"]:
            master_ip = repl_info["master_ip"]
            master_port = repl_info["master_port"]
            slave_ip = repl_info["slave_ip"]
            slave_port = repl_info["slave_port"]
            replic_tuple.append(
                {
                    "ejector": {"ip": master_ip, "port": master_port},
                    "receiver": {"ip": slave_ip, "port": slave_port},
                }
            )
        api.storage_instance_tuple.create(replic_tuple, creator=self.cluster["created_by"])
        return True

    def redis_instance(self) -> bool:
        """
        单redis主从实例填充cluster相关元数据
        """
        storages = [{"ip": self.cluster["master_ip"], "port": self.cluster["port"]}]
        domain_split = str.split(self.cluster["immute_domain"], ".")
        domain_split[0] = domain_split[0] + "-slave"
        slave_domain = ".".join(domain_split)
        handler = TendisSingleHandler
        handler.create(
            **{
                "bk_biz_id": self.cluster["bk_biz_id"],
                "bk_cloud_id": self.cluster["bk_cloud_id"],
                "name": self.cluster["cluster_name"],
                "alias": self.cluster["cluster_alias"],
                "major_version": self.cluster["db_version"],
                "db_module_id": DEFAULT_DB_MODULE_ID,
                "storages": storages,
                "immute_domain": self.cluster["immute_domain"],
                "slave_domain": slave_domain,
                "creator": self.cluster["created_by"],
                "region": self.cluster.get("region", ""),
                "disaster_tolerance_level": self.cluster.get("disaster_tolerance_level", ""),
            }
        )
        return True

    def redis_segment_make_cluster(self) -> bool:
        """
        twemproxy和redis实例关系关联
        """
        proxy_port = self.cluster["proxy_port"]
        proxies = [{"ip": proxy_ip, "port": proxy_port} for proxy_ip in self.cluster["new_proxy_ips"]]

        storages = []
        for server in self.cluster["servers"]:
            ip_port, _, seg_range, _ = server.split(SPACE_DIVIDER)
            ip, port = ip_port.split(IP_PORT_DIVIDER)
            storages.append({"ip": ip, "port": port, "seg_range": seg_range})
        if self.cluster["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance.value:
            handler = TendisCacheClusterHandler
        elif self.cluster["cluster_type"] == ClusterType.TwemproxyTendisSSDInstance.value:
            handler = TendisSSDClusterHandler
        else:
            raise Exception("unknown cluster type")
        handler.create(
            **{
                "bk_biz_id": self.cluster["bk_biz_id"],
                "bk_cloud_id": self.cluster["bk_cloud_id"],
                "name": self.cluster["cluster_name"],
                "alias": self.cluster["cluster_alias"],
                "major_version": self.cluster["db_version"],
                "immute_domain": self.cluster["immute_domain"],
                "db_module_id": DEFAULT_DB_MODULE_ID,
                "proxies": proxies,
                "storages": storages,
                "creator": self.cluster["created_by"],
                "region": self.cluster.get("region", ""),
                "disaster_tolerance_level": self.cluster.get("disaster_tolerance_level", ""),
            }
        )
        return True

    def redis_origin_make_cluster(self) -> bool:
        """
        cluster node模式建立集群关系
        """
        proxy_port = self.cluster["proxy_port"]
        proxies = [{"ip": proxy_ip, "port": proxy_port} for proxy_ip in self.cluster["new_proxy_ips"]]

        #  这里只传master
        storages = self.cluster["storages"]
        if self.cluster["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster.value:
            handler = TendisPlusClusterHandler
        elif self.cluster["cluster_type"] == ClusterType.TendisPredixyRedisCluster.value:
            handler = RedisClusterHandler
        else:
            raise Exception("unknown cluster type")
        handler.create(
            **{
                "bk_biz_id": self.cluster["bk_biz_id"],
                "bk_cloud_id": self.cluster["bk_cloud_id"],
                "name": self.cluster["cluster_name"],
                "alias": self.cluster["cluster_alias"],
                "major_version": self.cluster["db_version"],
                "immute_domain": self.cluster["immute_domain"],
                "db_module_id": DEFAULT_DB_MODULE_ID,
                "proxies": proxies,
                "storages": storages,
                "creator": self.cluster["created_by"],
                "region": self.cluster.get("region", ""),
                "disaster_tolerance_level": self.cluster.get("disaster_tolerance_level", ""),
            }
        )
        return True

    def get_cluster_id(self) -> (dict, bool):
        """
        根据bk_biz_id和domain获取cluster_id
        TODO 先直接通过对象操作，后面再改成接口
        """
        domain = self.ticket_data["domain_name"]

        cluster = Cluster.objects.get(bk_biz_id=self.ticket_data["bk_biz_id"], immute_domain=domain)
        if cluster.id is None or cluster.id == 0:
            return {}, False
        return {"cluster_id": cluster.id}, True

    def cluster_shutdown(self) -> bool:
        """
        集群下架
        """
        if self.cluster["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance.value:
            TendisCacheClusterHandler(
                bk_biz_id=self.ticket_data["bk_biz_id"], cluster_id=self.ticket_data["cluster_id"]
            ).decommission()
        elif self.cluster["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster.value:
            TendisPlusClusterHandler(
                bk_biz_id=self.ticket_data["bk_biz_id"], cluster_id=self.ticket_data["cluster_id"]
            ).decommission()
        elif self.cluster["cluster_type"] == ClusterType.TwemproxyTendisSSDInstance.value:
            TendisSSDClusterHandler(
                bk_biz_id=self.ticket_data["bk_biz_id"], cluster_id=self.ticket_data["cluster_id"]
            ).decommission()
        elif self.cluster["cluster_type"] == ClusterType.TendisPredixyRedisCluster.value:
            RedisClusterHandler(
                bk_biz_id=self.ticket_data["bk_biz_id"], cluster_id=self.ticket_data["cluster_id"]
            ).decommission()
        elif self.cluster["cluster_type"] == ClusterType.TendisRedisInstance.value:
            if "cluster_id" in self.cluster:
                cluster_id = self.cluster["cluster_id"]
            else:
                cluster_id = self.ticket_data["cluster_id"]
            TendisSingleHandler(bk_biz_id=self.ticket_data["bk_biz_id"], cluster_id=cluster_id).decommission()

        return True

    def instances_uninstall(self) -> bool:
        """
        Redis/Proxy 实例下架 {"ip":"","ports":[]}
        """
        with atomic():
            api.cluster.nosqlcomm.decommission_instances(
                ip=self.cluster["ip"], bk_cloud_id=self.cluster["bk_cloud_id"], ports=self.cluster["ports"]
            )
        return True

    def redis_redo_slaves(self) -> bool:
        """"""
        with atomic():
            for slave_info in self.cluster["old_slaves"]:
                StorageInstance.objects.filter(
                    machine__bk_cloud_id=self.cluster["bk_cloud_id"],
                    machine__ip=slave_info["ip"],
                    port__in=slave_info["ports"],
                ).update(status=InstanceStatus.UNAVAILABLE)
                logger.info(
                    "update old_slave {} ports: {} status to UNAVAILABLE".format(slave_info["ip"], slave_info["ports"])
                )
            cluster = Cluster.objects.get(
                bk_cloud_id=self.cluster["bk_cloud_id"], immute_domain=self.cluster["immute_domain"]
            )
            if cluster.cluster_type != ClusterType.TendisRedisInstance.value:
                # 集群
                api.cluster.nosqlcomm.redo_slaves(cluster, self.cluster["tendiss"], self.cluster["created_by"])
            else:
                # 主从
                for item in self.cluster["tendiss"]:
                    master_obj = StorageInstance.objects.get(
                        machine__bk_cloud_id=self.cluster["bk_cloud_id"],
                        machine__ip=item["ejector"]["ip"],
                        port=item["ejector"]["port"],
                    )
                    mycluster = master_obj.cluster.first()
                    if not mycluster:
                        raise Exception(
                            "not found master by master {}:{}".format(master_obj.machine.ip, master_obj.port)
                        )
                    logger.info(
                        "found cluster:{} by master {}:{}".format(
                            mycluster.immute_domain, master_obj.machine.ip, master_obj.port
                        )
                    )
                    api.cluster.nosqlcomm.redo_slaves(mycluster, [item], self.cluster["created_by"])
        return True

    def redis_replace_pair(self) -> bool:
        """
        创建主从关系， 然后在加入集群
        """
        with atomic():
            cluster = Cluster.objects.get(
                bk_cloud_id=self.cluster["bk_cloud_id"], immute_domain=self.cluster["immute_domain"]
            )
            tendiss = []
            for relation in self.cluster["sync_relation"]:
                receiver = relation["receiver"]
                slave_obj = StorageInstance.objects.get(machine__ip=receiver["ip"], port=receiver["port"])
                slave_obj.cluster_type = self.cluster["cluster_type"]
                slave_obj.instance_role = InstanceRole.REDIS_SLAVE.value
                slave_obj.instance_inner_role = InstanceInnerRole.SLAVE.value
                slave_obj.save(update_fields=["instance_role", "instance_inner_role", "cluster_type"])

                tendiss.append(
                    {
                        "ejector": relation["old_ejector"],
                        "receiver": relation["ejector"],
                    }
                )
            api.storage_instance_tuple.create(self.cluster["sync_relation"], creator=self.ticket_data["created_by"])
            api.cluster.nosqlcomm.make_sync(cluster=cluster, tendisss=tendiss)
        return True

    def instances_status_update(self) -> bool:
        """
        Redis/Proxy 实例修改实例状态 {"ip":"","ports":[],"status":11}
        """
        with atomic():
            machine_obj = Machine.objects.get(ip=self.cluster["meta_update_ip"])
            if machine_obj.access_layer == AccessLayer.PROXY.value:
                ProxyInstance.objects.filter(
                    machine__ip=self.cluster["meta_update_ip"], port__in=self.cluster["meta_update_ports"]
                ).update(status=self.cluster["meta_update_status"])
            else:
                # 支持互切的 不修改状态，保持 running
                if machine_obj.cluster_type not in [
                    ClusterType.TendisPredixyRedisCluster.value,
                    ClusterType.TendisPredixyTendisplusCluster.value,
                ]:
                    StorageInstance.objects.filter(
                        machine__ip=self.cluster["meta_update_ip"], port__in=self.cluster["meta_update_ports"]
                    ).update(status=self.cluster["meta_update_status"])
        return True

    def instances_failover_4_scene(self) -> bool:
        """1.修改状态、2.切换角色"""
        # 获取cluster
        cluster_obj = Cluster.objects.get(id=int(self.cluster["cluster_id"]))
        self.instances_status_update()
        with atomic():
            cc_manage, bk_host_ids = CcManage(int(self.cluster["bk_biz_id"]), cluster_obj.cluster_type), []
            for port in self.cluster["meta_update_ports"]:
                old_master = StorageInstance.objects.get(
                    machine__ip=self.cluster["meta_update_ip"],
                    port=port,
                    bk_biz_id=self.cluster["bk_biz_id"],
                    machine__bk_cloud_id=self.cluster["bk_cloud_id"],
                )
                old_slave = old_master.as_ejector.get().receiver

                bk_host_ids.append(old_master.machine.bk_host_id)
                bk_host_ids.append(old_slave.machine.bk_host_id)
                StorageInstanceTuple.objects.get(ejector=old_master, receiver=old_slave).delete(keep_parents=True)
                StorageInstanceTuple.objects.create(ejector=old_slave, receiver=old_master)
                old_master.instance_role = InstanceRole.REDIS_SLAVE.value
                old_master.instance_inner_role = InstanceInnerRole.SLAVE.value
                old_master.save(update_fields=["instance_role", "instance_inner_role"])

                # 切换新master服务实例角色标签
                cc_manage.add_label_for_service_instance(
                    bk_instance_ids=[old_master.bk_instance_id],
                    labels_dict={"instance_role": InstanceRole.REDIS_SLAVE.value},
                )

                # 切换新slave服务实例角色标签
                cc_manage.add_label_for_service_instance(
                    bk_instance_ids=[old_slave.bk_instance_id],
                    labels_dict={"instance_role": InstanceRole.REDIS_MASTER.value},
                )
            cc_manage.update_host_properties(bk_host_ids)
        return True

    def tendis_switch_4_scene(self):
        """切换 nosql_set_dtl, 挪动CC 模块"""
        cluster = Cluster.objects.get(
            bk_cloud_id=self.cluster["bk_cloud_id"], immute_domain=self.cluster["immute_domain"]
        )
        api.cluster.nosqlcomm.switch_tendis(
            cluster=cluster,
            tendisss=self.cluster["sync_relation"],
            switch_type=self.cluster["switch_condition"]["sync_type"],
        )
        if "origin_db_version" in self.cluster:
            if self.cluster["origin_db_version"] != self.cluster["db_version"]:
                cluster.major_version = self.cluster["db_version"]
                cluster.save()

    def update_rollback_task_status(self) -> bool:
        """
        更新构造记录为已销毁
        """
        task = TbTendisRollbackTasks.objects.filter(
            related_rollback_bill_id=self.cluster["related_rollback_bill_id"],
            bk_biz_id=self.cluster["bk_biz_id"],
            prod_cluster=self.cluster["prod_cluster"],
        ).update(destroyed_status=self.cluster["destroyed_status"])
        return task

    def __get_cluster_config(self, domain_name: str, db_version: str, conf_type: str, namespace: str) -> Any:
        """
        获取已部署的实例配置
        """

        data = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(self.ticket_data["bk_biz_id"]),
                "level_name": LevelName.CLUSTER,
                "level_value": domain_name,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "conf_file": db_version,
                "conf_type": conf_type,
                "namespace": namespace,
                "format": FormatType.MAP,
            }
        )
        return data["content"]

    @transaction.atomic
    def data_construction_tasks_operate(self):
        """
        写入构造记录元数据
        """

        passwd_ret = PayloadHandler.redis_get_password_by_domain(self.cluster["domain_name"])
        task = TbTendisRollbackTasks(
            creator=self.ticket_data["created_by"],
            related_rollback_bill_id=self.ticket_data["uid"],
            bk_biz_id=self.ticket_data["bk_biz_id"],
            bk_cloud_id=self.cluster["bk_cloud_id"],
            prod_cluster_type=self.cluster["prod_cluster_type"],
            prod_cluster_id=self.cluster["prod_cluster_id"],
            specification=self.cluster["specification"],
            prod_cluster=self.cluster["prod_cluster"],
            prod_instance_range=self.cluster["prod_instance_range"],
            temp_cluster_type=self.cluster["temp_cluster_type"],
            temp_instance_range=self.cluster["temp_instance_range"],
            temp_proxy_password=base64.b64encode(passwd_ret.get("redis_proxy_password").encode("utf-8")),
            temp_cluster_proxy=self.cluster["temp_cluster_proxy"],
            prod_temp_instance_pairs=self.cluster["prod_temp_instance_pairs"],
            host_count=self.cluster["host_count"],
            recovery_time_point=self.cluster["recovery_time_point"],
            status=self.cluster["status"],
            temp_redis_password=base64.b64encode(passwd_ret.get("redis_password").encode("utf-8")),
        )
        task.save()

    def redis_rollback_host_transfer(self) -> bool:
        """
        数据构造临时机器挪动cc模块到对应源集群下
        """
        with atomic():
            receiver_objs = []
            for ins in self.cluster["tendiss"]:
                new_ejector_obj = StorageInstance.objects.get(
                    machine__ip=ins["receiver"]["ip"], port=ins["receiver"]["port"]
                )
                logger.info(" need move cc module")
                receiver_objs.append(new_ejector_obj)
            cluster = Cluster.objects.get(
                bk_cloud_id=self.cluster["bk_cloud_id"], immute_domain=self.cluster["immute_domain"]
            )
            RedisCCTopoOperator(cluster).transfer_instances_to_cluster_module(receiver_objs)
        return True

    def redis_role_swap_4_scene(self) -> bool:
        """
        主从互切 [仅RedisCluster 类型]
                act_kwargs.cluster["role_swap_host"].append({"new_ejector":new_host_master,"new_receiver":old_master})
        """
        # 获取cluster
        cluster_id = self.cluster["cluster_id"]
        cluster = Cluster.objects.get(id=cluster_id)

        cc_manage = CcManage(int(self.cluster["bk_biz_id"]), cluster.cluster_type)
        with atomic():
            for ins in self.cluster["role_swap_ins"]:
                ins1 = StorageInstance.objects.get(
                    machine__ip=ins["new_receiver_ip"],
                    port=ins["new_receiver_port"],
                    machine__bk_cloud_id=self.cluster["bk_cloud_id"],
                    bk_biz_id=self.cluster["bk_biz_id"],
                )
                ins2 = StorageInstance.objects.get(
                    machine__ip=ins["new_ejector_ip"],
                    port=ins["new_ejector_port"],
                    machine__bk_cloud_id=self.cluster["bk_cloud_id"],
                    bk_biz_id=self.cluster["bk_biz_id"],
                )

                # 变更同步关系
                StorageInstanceTuple.objects.get(ejector=ins1, receiver=ins2).delete(keep_parents=True)
                StorageInstanceTuple.objects.create(ejector=ins2, receiver=ins1)

                # 变更角色
                ins1.instance_role = InstanceRole.REDIS_SLAVE.value
                ins1.instance_inner_role = InstanceInnerRole.SLAVE.value

                ins2.instance_role = InstanceRole.REDIS_MASTER.value
                ins2.instance_inner_role = InstanceInnerRole.MASTER.value

                ins1.save(update_fields=["instance_role", "instance_inner_role"])
                ins2.save(update_fields=["instance_role", "instance_inner_role"])

                # 切换新master服务实例角色标签
                cc_manage.add_label_for_service_instance(
                    bk_instance_ids=[ins1.bk_instance_id],
                    labels_dict={"instance_role": InstanceRole.REDIS_SLAVE.value},
                )

                # 切换新slave服务实例角色标签
                cc_manage.add_label_for_service_instance(
                    bk_instance_ids=[ins2.bk_instance_id],
                    labels_dict={"instance_role": InstanceRole.REDIS_MASTER.value},
                )

        return True

    def add_clb_domain(self):
        """
        增加clb记录
        """
        entry_type = ClusterEntryType.CLB
        cluster = Cluster.objects.get(
            bk_cloud_id=self.cluster["bk_cloud_id"], immute_domain=self.cluster["immute_domain"]
        )
        proxy_objs = cluster.proxyinstance_set.all()
        clb_cluster_entry = ClusterEntry.objects.create(
            cluster=cluster,
            cluster_entry_type=entry_type,
            entry=self.cluster["ip"],
            creator=self.cluster["created_by"],
        )
        clb_cluster_entry.save()
        clb_cluster_entry.proxyinstance_set.add(*proxy_objs)
        clb_domain = ""
        if "clb_domain" in self.cluster:
            clb_domain = self.cluster["clb_domain"]
        if clb_domain != "":
            entry_type = ClusterEntryType.CLBDNS
            clbdns_cluster_entry = ClusterEntry.objects.create(
                cluster=cluster,
                cluster_entry_type=entry_type,
                forward_to_id=clb_cluster_entry.id,
                entry=clb_domain,
                creator=self.cluster["created_by"],
            )
            clbdns_cluster_entry.save()
            clbdns_cluster_entry.proxyinstance_set.add(*proxy_objs)
        clb_entry = CLBEntryDetail.objects.create(
            clb_ip=self.cluster["ip"],
            clb_id=self.cluster["id"],
            listener_id=self.cluster["listener_id"],
            clb_region=self.cluster["region"],
            entry_id=clb_cluster_entry.id,
            creator=self.cluster["created_by"],
        )
        clb_entry.save()

    @transaction.atomic
    def tendisplus_add_instance_pairs(self):
        """
        tendisplus集群添加实例对
        self.cluster["params"] =
        {
            "cluster_id":51,
            "replication_pairs":[
                {
                    "master":{
                        "ip":"a.a.a.a.",
                        "port":30000
                    },
                    "slave":{
                        "ip":"b.b.b.b",
                        "port":30000
                    },
                }
            ]
        }
        """
        params = self.cluster["params"]
        cluster = Cluster.objects.get(id=params["cluster_id"])
        dns_manage = DnsManage(bk_biz_id=cluster.bk_biz_id, bk_cloud_id=cluster.bk_cloud_id)
        all_instances, bk_host_ids = [], []
        for replication_pair in params["replication_pairs"]:
            master_ip = replication_pair["master"]["ip"]
            master_port = replication_pair["master"]["port"]
            slave_ip = replication_pair["slave"]["ip"]
            slave_port = replication_pair["slave"]["port"]
            master_obj = StorageInstance.objects.get(
                machine__ip=master_ip,
                port=master_port,
                machine__bk_cloud_id=cluster.bk_cloud_id,
                bk_biz_id=cluster.bk_biz_id,
            )
            slave_obj = StorageInstance.objects.get(
                machine__ip=slave_ip,
                port=slave_port,
                machine__bk_cloud_id=cluster.bk_cloud_id,
                bk_biz_id=cluster.bk_biz_id,
            )
            all_instances.append(master_obj)
            all_instances.append(slave_obj)
            bk_host_ids.append(master_obj.machine.bk_host_id)
            bk_host_ids.append(slave_obj.machine.bk_host_id)
            master_instance = "{}#{}".format(master_obj.machine.ip, master_obj.port)
            slave_instance = "{}#{}".format(slave_obj.machine.ip, slave_obj.port)
            # 更新 StorageInstance
            logger.info("update master {} role & cluster_type".format(master_obj.ip_port))
            master_obj.instance_role = InstanceRole.REDIS_MASTER
            master_obj.instance_inner_role = InstanceInnerRole.MASTER
            master_obj.cluster_type = cluster.cluster_type
            master_obj.save(update_fields=["instance_role", "instance_inner_role", "cluster_type"])
            logger.info("update slave {} role & cluster_type".format(slave_obj.ip_port))
            slave_obj.instance_role = InstanceRole.REDIS_SLAVE
            slave_obj.instance_inner_role = InstanceInnerRole.SLAVE
            slave_obj.cluster_type = cluster.cluster_type
            slave_obj.save(update_fields=["instance_role", "instance_inner_role", "cluster_type"])
            # 更新 StorageInstanceTuple
            inst_tuple = StorageInstanceTuple.objects.filter(ejector=master_obj, receiver=slave_obj)
            if not inst_tuple:
                logger.info(
                    "create StorageInstanceTuple ejector {} receiver {}".format(master_obj.ip_port, slave_obj.ip_port)
                )
                StorageInstanceTuple.objects.create(ejector=master_obj, receiver=slave_obj)
            # proxy 添加 master_obj
            logger.info(
                "cluster {} proxyinstances add {} {}".format(
                    cluster.immute_domain, master_obj.ip_port, slave_obj.ip_port
                )
            )
            for proxy_inst in cluster.proxyinstance_set.all():
                proxy_inst.storageinstance.add(master_obj)
            # 更新cluster.storageinstance_set
            cluster.storageinstance_set.add(master_obj)
            cluster.storageinstance_set.add(slave_obj)
            # 更新 nodes. 域名 以及 对应的 cluster_entry信息
            cluster_entry = cluster.clusterentry_set.filter(role=ClusterEntryRole.NODE_ENTRY.value).first()
            if (
                cluster_entry
                and cluster_entry.entry.startswith("nodes.")
                and master_obj.port == DEFAULT_REDIS_START_PORT
            ):
                logger.info(
                    "cluster {} cluster_entry {} add {} {}".format(
                        cluster.immute_domain, cluster_entry.entry, master_obj.ip_port, slave_obj.ip_port
                    )
                )
                cluster_entry.storageinstance_set.add(master_obj)
                cluster_entry.storageinstance_set.add(slave_obj)
                logger.info(
                    "nodes.domain {} update dns add {} {}".format(cluster_entry.entry, master_instance, slave_instance)
                )
                dns_manage.create_domain(
                    add_domain_name=cluster_entry.entry, instance_list=[master_instance, slave_instance]
                )
        # 更新所有实例的模块信息
        logger.info("cluster {} all instances {} update module".format(cluster.immute_domain, all_instances))
        RedisCCTopoOperator(cluster).transfer_instances_to_cluster_module(all_instances)
        CcManage(cluster.bk_biz_id, cluster.cluster_type).update_host_properties(bk_host_ids)

    @transaction.atomic
    def tendisplus_remove_instance_pair(self):
        """
        tendisplus集群删除实例对
        self.cluster["params"] =
        {
            "cluster_id":51,
            "replication_pairs":[
                {
                    "master":{
                        "ip":"a.a.a.a.",
                        "port":30000
                    },
                    "slave":{
                        "ip":"b.b.b.b",
                        "port":30000
                    },
                }
            ]
        }
        """
        params = self.cluster["params"]
        cluster = Cluster.objects.get(id=params["cluster_id"])
        dns_manage = DnsManage(bk_biz_id=cluster.bk_biz_id, bk_cloud_id=cluster.bk_cloud_id)
        for replication_pair in params["replication_pairs"]:
            master_ip = replication_pair["master"]["ip"]
            master_port = replication_pair["master"]["port"]
            slave_ip = replication_pair["slave"]["ip"]
            slave_port = replication_pair["slave"]["port"]
            master_obj = StorageInstance.objects.get(
                machine__ip=master_ip,
                port=master_port,
                machine__bk_cloud_id=cluster.bk_cloud_id,
                bk_biz_id=cluster.bk_biz_id,
            )
            slave_obj = StorageInstance.objects.get(
                machine__ip=slave_ip,
                port=slave_port,
                machine__bk_cloud_id=cluster.bk_cloud_id,
                bk_biz_id=cluster.bk_biz_id,
            )
            master_instance = "{}#{}".format(master_obj.machine.ip, master_obj.port)
            slave_instance = "{}#{}".format(slave_obj.machine.ip, slave_obj.port)
            # 删除StorageInstanceTuple关系
            inst_tuple = StorageInstanceTuple.objects.filter(ejector=master_obj, receiver=slave_obj)
            if inst_tuple:
                logger.info(
                    "delete StorageInstanceTuple ejector {} receiver {}".format(master_obj.ip_port, slave_obj.ip_port)
                )
                inst_tuple.delete()
            # 删除proxy实例关系
            logger.info("cluster {} proxyinstances remove master {}".format(cluster.immute_domain, master_obj.ip_port))
            for proxy_inst in cluster.proxyinstance_set.all():
                proxy_inst.storageinstance.remove(master_obj)
            # 删除cluster.storageinstance_set关系
            cluster.storageinstance_set.remove(master_obj)
            cluster.storageinstance_set.remove(slave_obj)
            # 删除nodes.节点域名
            cluster_entry = cluster.clusterentry_set.filter(role=ClusterEntryRole.NODE_ENTRY.value).first()
            if (
                cluster_entry
                and cluster_entry.entry.startswith("nodes.")
                and master_obj.port == DEFAULT_REDIS_START_PORT
            ):
                logger.info(
                    "cluster {} cluster_entry {} remove {} {}".format(
                        cluster.immute_domain, cluster_entry.entry, master_instance, slave_instance
                    )
                )
                cluster_entry.storageinstance_set.remove(master_obj)
                cluster_entry.storageinstance_set.remove(slave_obj)
                dns_manage.recycle_domain_record(del_instance_list=[master_instance, slave_instance])
        # 模块信息等下架时候再更新

    @transaction.atomic
    def cluster_add_slave_update_meta(self):
        """
        集群添加从节点
        cluster['params']=[
        {
            "cluster_id":50,
            "replication_pairs":[
                {
                    "master":{
                        "ip":"a.a.a.a",
                        "port":30000
                    },
                    "new_slave":{
                        "ip":"b.b.b.b",
                        "port":30000
                    },
                },
                {
                    "master":{
                        "ip":"a.a.a.a",
                        "port":30001
                    },
                    "new_slave":{
                        "ip":"b.b.b.b",
                        "port":30001
                    },
                }
            ]
        }]
        """
        for param in self.cluster["params"]:
            cluster, bk_host_ids = Cluster.objects.get(id=param["cluster_id"]), []
            for replication_pair in param["replication_pairs"]:
                master_ip = replication_pair["master"]["ip"]
                master_port = replication_pair["master"]["port"]
                new_slave_ip = replication_pair["new_slave"]["ip"]
                new_slave_port = replication_pair["new_slave"]["port"]

                master_obj = cluster.storageinstance_set.get(machine__ip=master_ip, port=master_port)
                old_slave_obj = None
                if master_obj.as_ejector and master_obj.as_ejector.first():
                    old_slave_obj = master_obj.as_ejector.get().receiver
                new_slave_obj = StorageInstance.objects.get(
                    machine__ip=new_slave_ip,
                    port=new_slave_port,
                    machine__bk_cloud_id=cluster.bk_cloud_id,
                    bk_biz_id=cluster.bk_biz_id,
                )

                # 更新 StorageInstance
                logger.info("update new slave {} role & cluster_type".format(new_slave_obj.ip_port))
                new_slave_obj.instance_role = InstanceRole.REDIS_SLAVE
                new_slave_obj.instance_inner_role = InstanceInnerRole.SLAVE
                new_slave_obj.cluster_type = cluster.cluster_type
                new_slave_obj.save(update_fields=["instance_role", "instance_inner_role", "cluster_type"])
                bk_host_ids.append(new_slave_obj.machine.bk_host_id)

                # 更新 machine
                new_slave_machine = new_slave_obj.machine
                logger.info(
                    "update new slave machine {} cluster_type {}".format(new_slave_machine.ip, cluster.cluster_type)
                )
                new_slave_machine.cluster_type = cluster.cluster_type
                new_slave_machine.save(update_fields=["cluster_type"])

                # 更新 StorageInstanceTuple
                logger.info(
                    "update StorageInstanceTuple master {} slave {}".format(master_obj.ip_port, new_slave_obj.ip_port)
                )
                StorageInstanceTuple.objects.filter(ejector=master_obj).update(
                    ejector=master_obj, receiver=new_slave_obj
                )

                # 更新 cluster.storageinstance_set
                logger.info(
                    "cluster {} storageinstance_set add new slave {}".format(
                        cluster.immute_domain, new_slave_obj.ip_port
                    )
                )
                cluster.storageinstance_set.add(new_slave_obj)
                if old_slave_obj and old_slave_obj.ip_port != new_slave_obj.ip_port:
                    cluster.storageinstance_set.remove(old_slave_obj)

                if cluster.cluster_type == ClusterType.TendisRedisInstance:
                    # 更新 cluster.clusterentry_set 和域名信息
                    slave_domain = ""
                    for entry_obj in cluster.clusterentry_set.filter(role=ClusterEntryRole.SLAVE_ENTRY):
                        slave_domain = entry_obj.entry
                        entry_obj.storageinstance_set.add(new_slave_obj)
                        entry_obj.storageinstance_set.remove(master_obj)
                        if old_slave_obj and old_slave_obj.ip_port != new_slave_obj.ip_port:
                            entry_obj.storageinstance_set.remove(old_slave_obj)
                    if slave_domain != "":
                        # 更新slave域名信息
                        dns_manage = DnsManage(bk_biz_id=cluster.bk_biz_id, bk_cloud_id=cluster.bk_cloud_id)
                        exists_insts = []
                        for row in dns_manage.get_domain(domain_name=slave_domain):
                            exists_insts.append("{}#{}".format(row["ip"], row["port"]))
                        # 先删除
                        if exists_insts:
                            logger.info("domain {} remove instances {}".format(slave_domain, exists_insts))
                            dns_manage.remove_domain_ip(domain=slave_domain, del_instance_list=exists_insts)
                        # 再添加
                        new_insts = [f"{new_slave_obj.machine.ip}#{new_slave_obj.port}"]
                        logger.info("domain {} add instances {}".format(slave_domain, new_insts))
                        dns_manage.create_domain(add_domain_name=slave_domain, instance_list=new_insts)

                # 更新 nodes. 域名对应的 cluster_entry信息
                cluster_entry = cluster.clusterentry_set.filter(role=ClusterEntryRole.NODE_ENTRY.value).first()
                if cluster_entry and cluster_entry.entry.startswith("nodes."):
                    cluster_entry.storageinstance_set.add(new_slave_obj)
                # 更新模块信息
                is_increment = False
                if cluster.cluster_type == ClusterType.TendisRedisInstance:
                    is_increment = True
                RedisCCTopoOperator(cluster).transfer_instances_to_cluster_module(
                    [new_slave_obj], is_increment=is_increment
                )
            CcManage(cluster.bk_biz_id, cluster.cluster_type).update_host_properties(bk_host_ids)

    @transaction.atomic
    def switch_dns_for_redis_instance_version_upgrade(self):
        cluster_ids = self.cluster["cluster_ids"]
        for cluster_id in cluster_ids:
            cluster = Cluster.objects.get(id=cluster_id)
            old_master_obj = cluster.storageinstance_set.get(instance_role=InstanceRole.REDIS_MASTER.value)
            old_slave_obj = old_master_obj.as_ejector.get().receiver
            new_slave_obj = old_master_obj
            new_master_obj = old_slave_obj

            master_domain = ""
            for entry_obj in cluster.clusterentry_set.filter(role=ClusterEntryRole.MASTER_ENTRY):
                master_domain = entry_obj.entry
            slave_domain = ""
            for entry_obj in cluster.clusterentry_set.filter(role=ClusterEntryRole.SLAVE_ENTRY):
                slave_domain = entry_obj.entry
            # 更新域名信息
            dns_manage = DnsManage(bk_biz_id=cluster.bk_biz_id, bk_cloud_id=cluster.bk_cloud_id)

            old_master_instance = "{}#{}".format(old_master_obj.machine.ip, old_master_obj.port)
            old_slave_instance = "{}#{}".format(old_slave_obj.machine.ip, old_slave_obj.port)
            new_master_instance = "{}#{}".format(new_master_obj.machine.ip, new_master_obj.port)
            new_slave_instance = "{}#{}".format(new_slave_obj.machine.ip, new_slave_obj.port)

            logger.info(
                "master_domain {} update from {} to {}".format(master_domain, old_master_instance, new_master_instance)
            )
            dns_manage.update_domain(
                old_instance=old_master_instance, new_instance=new_master_instance, update_domain_name=master_domain
            )

            logger.info(
                "slave_domain {} update from {} to {}".format(slave_domain, old_slave_instance, new_slave_instance)
            )
            dns_manage.update_domain(
                old_instance=old_slave_instance, new_instance=new_slave_instance, update_domain_name=slave_domain
            )

    @transaction.atomic
    def update_meta_for_redis_instance_version_upgrade(self):
        cluster_ids, bk_host_ids = self.cluster["cluster_ids"], []
        for cluster_id in cluster_ids:
            cluster = Cluster.objects.get(id=cluster_id)
            old_master_obj = cluster.storageinstance_set.get(instance_role=InstanceRole.REDIS_MASTER.value)
            old_slave_obj = old_master_obj.as_ejector.get().receiver

            new_slave_obj = old_master_obj
            new_master_obj = old_slave_obj
            bk_host_ids.append(new_slave_obj.machine.bk_host_id)
            bk_host_ids.append(new_master_obj.machine.bk_host_id)

            logger.info("new_master {} update role ro redis_master".format(new_master_obj.ip_port))
            new_master_obj.instance_role = InstanceRole.REDIS_MASTER
            new_master_obj.instance_inner_role = InstanceInnerRole.MASTER
            new_master_obj.save(update_fields=["instance_role", "instance_inner_role"])

            logger.info("new_slave {} update role ro redis_slave".format(new_slave_obj.ip_port))
            new_slave_obj.instance_role = InstanceRole.REDIS_SLAVE
            new_slave_obj.instance_inner_role = InstanceInnerRole.SLAVE
            new_slave_obj.save(update_fields=["instance_role", "instance_inner_role"])

            StorageInstanceTuple.objects.filter(ejector=old_master_obj, receiver=old_slave_obj).update(
                ejector=new_master_obj, receiver=new_slave_obj
            )

            # cluster.storageinstance_set.all() 不用变, master/slave instance 都在

            # cluster.clusterentry_set 更新
            for entry_obj in cluster.clusterentry_set.filter(role=ClusterEntryRole.MASTER_ENTRY):
                entry_obj.storageinstance_set.add(new_master_obj)
                entry_obj.storageinstance_set.remove(new_slave_obj)
                logger.info(
                    "cluster_master_entry {} add {},remove {}".format(entry_obj, new_master_obj, new_slave_obj)
                )

            for entry_obj in cluster.clusterentry_set.filter(role=ClusterEntryRole.SLAVE_ENTRY):
                entry_obj.storageinstance_set.add(new_slave_obj)
                entry_obj.storageinstance_set.remove(new_master_obj)
                logger.info("cluster_slave_entry {} add {},remove {}".format(entry_obj, new_slave_obj, new_master_obj))

            # 修改模块
            RedisCCTopoOperator(cluster).transfer_instances_to_cluster_module(
                [new_master_obj, new_slave_obj], is_increment=False
            )
        CcManage(cluster.bk_biz_id, cluster.cluster_type).update_host_properties(bk_host_ids)

    def add_polairs_domain(self):
        """
        增加polairs记录
        """
        cluster = Cluster.objects.get(
            bk_cloud_id=self.cluster["bk_cloud_id"], immute_domain=self.cluster["immute_domain"]
        )
        proxy_objs = cluster.proxyinstance_set.all()
        cluster_entry = ClusterEntry.objects.create(
            cluster=cluster,
            cluster_entry_type=ClusterEntryType.POLARIS,
            entry=self.cluster["name"],
            creator=self.cluster["created_by"],
        )
        cluster_entry.save()
        cluster_entry.proxyinstance_set.add(*proxy_objs)
        alias_token = ""
        if self.cluster.get("alias_token"):
            alias_token = self.cluster["alias_token"]
        polaris_entry = PolarisEntryDetail.objects.create(
            polaris_name=self.cluster["name"],
            # 历史原因，可能存在没有l5字段的集群
            polaris_l5=self.cluster.get("l5", ""),
            polaris_token=self.cluster["token"],
            alias_token=alias_token,
            entry_id=cluster_entry.id,
            creator=self.cluster["created_by"],
        )
        polaris_entry.save()

    def tendis_add_clb_domain_4_scene(self):
        """增加CLB 域名"""
        cluster = Cluster.objects.get(
            bk_cloud_id=self.cluster["bk_cloud_id"], immute_domain=self.cluster["immute_domain"]
        )
        clb = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB.value).first()
        logger.info("add clb domain 4 clb.{} : {}".format(cluster.immute_domain, clb.entry))
        cluster_entry = ClusterEntry.objects.create(
            cluster=cluster,
            cluster_entry_type=ClusterEntryType.CLBDNS,
            entry="clb.{}".format(cluster.immute_domain),
            creator=self.ticket_data["created_by"],
            forward_to_id=clb.id,
        )
        cluster_entry.save()

    def tendis_bind_clb_domain_4_scene(self):
        """主域名直接指向CLB"""
        cluster = Cluster.objects.get(
            bk_cloud_id=self.cluster["bk_cloud_id"], immute_domain=self.cluster["immute_domain"]
        )
        immute_entry = cluster.clusterentry_set.filter(
            cluster_entry_type=ClusterEntryType.DNS.value, entry=cluster.immute_domain
        ).first()
        clb_entry = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB.value).first()

        logger.info("bind immute domain {} 2 clb {}".format(cluster.immute_domain, clb_entry.entry))
        immute_entry.forward_to_id = clb_entry.id
        immute_entry.creator = self.ticket_data["created_by"]
        immute_entry.save(update_fields=["forward_to_id", "creator"])

    # 主域名解绑CLB
    def tendis_unBind_clb_domain_4_scene(self):
        """主域名解绑CLB"""
        cluster = Cluster.objects.get(
            bk_cloud_id=self.cluster["bk_cloud_id"], immute_domain=self.cluster["immute_domain"]
        )
        immute_entry = cluster.clusterentry_set.filter(
            cluster_entry_type=ClusterEntryType.DNS.value, entry=cluster.immute_domain
        ).first()
        logger.info("Unbind immute domain {} 2 clbid: {}".format(cluster.immute_domain, immute_entry.forward_to_id))

        immute_entry.forward_to_id = None
        immute_entry.creator = self.ticket_data["created_by"]
        immute_entry.save(update_fields=["forward_to_id", "creator"])

    def get_inst_list(self, storageinstances) -> list:
        src_host = []
        for inst in storageinstances:
            src_host.append({"host_id": inst.machine.bk_host_id, "ip": inst.machine.ip, "port": inst.port})
        return src_host

    def dts_switch_update_cluster_entry(self, cluster: Cluster):
        """
        dts切换,更新集群的 cluster node_entry 信息
        """
        cluster_entry = cluster.clusterentry_set.filter(role=ClusterEntryRole.NODE_ENTRY.value).first()
        nodes_domain = "nodes." + cluster.immute_domain
        storageinstances = cluster.storageinstance_set.all()
        if is_redis_cluster_protocal(cluster.cluster_type):
            if not cluster_entry:
                # 应该存在的,没存在,则新增
                cluster_entry = ClusterEntry.objects.create(
                    cluster=cluster,
                    cluster_entry_type=ClusterEntryType.DNS,
                    entry=nodes_domain,
                    creator=cluster.creator,
                    role=ClusterEntryRole.NODE_ENTRY,
                )
                cluster_entry.storageinstance_set.add(*storageinstances)
                cluster_entry.save()
                logger.info(
                    _("redis集群:%s cluster_type:%s 新增 %s cluster_entry").format(
                        cluster.immute_domain, cluster.cluster_type, nodes_domain
                    )
                )
            else:
                # 应该存在的,确实存在,则更新
                cluster_entry.storageinstance_set.clear()
                cluster_entry.storageinstance_set.add(*storageinstances)
                cluster_entry.save()
                logger.info(
                    _("redis集群:%s cluster_type:%s 更新 cluster_entry:%s").format(
                        cluster.immute_domain, cluster.cluster_type, cluster_entry.entry
                    )
                )
        else:
            if cluster_entry:
                #  不该存在的,存在了,则删除
                cluster_entry.storageinstance_set.clear()
                cluster_entry.delete()
                logger.info(
                    _("redis集群:%s cluster_type:%s 删除 cluster_entry:%s").format(
                        cluster.immute_domain, cluster.cluster_type, nodes_domain
                    )
                )

    def dts_online_switch_swap_two_cluster_storage(self):
        """
        dts在线切换,交换两个集群的storageinstances
        """
        src_cluster_id: int = self.cluster["src_cluster_id"]
        dst_cluster_id: int = self.cluster["dst_cluster_id"]
        src_cluster = Cluster.objects.get(id=src_cluster_id)
        dst_cluster = Cluster.objects.get(id=dst_cluster_id)
        src_proxyinstances = copy.deepcopy(src_cluster.proxyinstance_set.all())
        dst_proxyinstances = copy.deepcopy(dst_cluster.proxyinstance_set.all())

        src_proxy_storageinstances = copy.deepcopy(src_proxyinstances[0].storageinstance.all())
        dst_proxy_storageinstances = copy.deepcopy(dst_proxyinstances[0].storageinstance.all())

        src_storageinstances = copy.deepcopy(src_cluster.storageinstance_set.all())
        dst_storageinstances = copy.deepcopy(dst_cluster.storageinstance_set.all())

        src_nosqldtl = copy.deepcopy(src_cluster.nosqlstoragesetdtl_set.all())
        dst_nosqldtl = copy.deepcopy(dst_cluster.nosqlstoragesetdtl_set.all())

        logger.info(
            _("dts_online_switch_swap_two_cluster_storage 1111 first get src_inst_list:{}").format(
                self.get_inst_list(src_storageinstances)
            )
        )
        logger.info(
            _("dts_online_switch_swap_two_cluster_storage 1111 first get src dst_inst_list:{}").format(
                self.get_inst_list(dst_storageinstances)
            )
        )

        src_cluster_info: dict = {
            "cluster_type": src_cluster.cluster_type,
            "major_version": src_cluster.major_version,
            "region": src_cluster.region,
            "db_module_id": src_cluster.db_module_id,
            "proxy_machine_type": src_proxyinstances[0].machine_type,
        }
        dst_cluster_info: dict = {
            "cluster_type": dst_cluster.cluster_type,
            "major_version": dst_cluster.major_version,
            "region": dst_cluster.region,
            "db_module_id": dst_cluster.db_module_id,
            "proxy_machine_type": dst_proxyinstances[0].machine_type,
        }

        with atomic():
            # 交换cluster_type 等信息
            logger.info(_("dts 交换两个集群的 cluster_type 等信息"))
            src_cluster.cluster_type = dst_cluster_info["cluster_type"]
            src_cluster.major_version = dst_cluster_info["major_version"]
            src_cluster.region = dst_cluster_info["region"]
            src_cluster.db_module_id = dst_cluster_info["db_module_id"]

            dst_cluster.cluster_type = src_cluster_info["cluster_type"]
            dst_cluster.major_version = src_cluster_info["major_version"]
            dst_cluster.region = src_cluster_info["region"]
            dst_cluster.db_module_id = src_cluster_info["db_module_id"]

            # 交换cluster storageinstances
            logger.info(_("dts 交换两个集群的 storageinstances"))
            src_cluster.storageinstance_set.clear()
            src_cluster.storageinstance_set.add(*dst_storageinstances)
            src_cluster.save()

            dst_cluster.storageinstance_set.clear()
            dst_cluster.storageinstance_set.add(*src_storageinstances)
            dst_cluster.save()

            logger.info(
                _("dts_online_switch_swap_two_cluster_storage 2222 交换两个集群strorageinstance完成 src_inst_list:{}").format(
                    self.get_inst_list(src_storageinstances)
                )
            )
            logger.info(
                _("dts_online_switch_swap_two_cluster_storage 2222 交换两个集群strorageinstance完成 dst_inst_list:{}").format(
                    self.get_inst_list(dst_storageinstances)
                )
            )

            # 交换cluster nosqlstoragesetdtl
            logger.info(_("dts 交换两个集群的 nosqlstoragesetdtl"))
            for nosqldtl_obj in src_nosqldtl:
                nosqldtl_obj.cluster = dst_cluster
                nosqldtl_obj.save()

            for nosqldtl_obj in dst_nosqldtl:
                nosqldtl_obj.cluster = src_cluster
                nosqldtl_obj.save()

            # 交换proxy storageinstances 和 machine_type
            logger.info(_("dts 交换两个集群 proxy 的 storageinstances"))
            for src_proxy in src_proxyinstances:
                src_proxy.storageinstance.clear()
                src_proxy.storageinstance.add(*dst_proxy_storageinstances)

                src_proxy.machine_type = dst_cluster_info["proxy_machine_type"]
                src_proxy.save()

                src_proxy.machine.machine_type = dst_cluster_info["proxy_machine_type"]
                src_proxy.machine.save(update_fields=["machine_type"])
            update_cluster_type(src_proxyinstances, dst_cluster_info["cluster_type"])

            for dst_proxy in dst_proxyinstances:
                dst_proxy.storageinstance.clear()
                dst_proxy.storageinstance.add(*src_proxy_storageinstances)

                dst_proxy.machine_type = src_cluster_info["proxy_machine_type"]
                dst_proxy.save()

                dst_proxy.machine.machine_type = src_cluster_info["proxy_machine_type"]
                dst_proxy.machine.save(update_fields=["machine_type"])
            update_cluster_type(dst_proxyinstances, src_cluster_info["cluster_type"])

            # 更新cluster node_entry
            self.dts_switch_update_cluster_entry(src_cluster)
            self.dts_switch_update_cluster_entry(dst_cluster)

            # 交换 cc module
            logger.info(_("dts 交换两个集群的 cc module"))
            logger.info(
                _(
                    "dts_online_switch_swap_two_cluster_storage 3333 转移目标机器模块到源集群下,src_cluster:{} dst_inst_list:{}"
                ).format(src_cluster.immute_domain, self.get_inst_list(dst_storageinstances))
            )
            RedisCCTopoOperator(src_cluster).transfer_instances_to_cluster_module(dst_storageinstances)
            logger.info(
                _(
                    "dts_online_switch_swap_two_cluster_storage 3333 转移源机器模块到目标集群下,dst_cluster:{} src_inst_list:{}"
                ).format(dst_cluster.immute_domain, self.get_inst_list(src_storageinstances))
            )
            RedisCCTopoOperator(dst_cluster).transfer_instances_to_cluster_module(src_storageinstances)
            # 两个集群的 proxy ip均是不变的,但类型变化后,模块信息需变化
            RedisCCTopoOperator(src_cluster).transfer_instances_to_cluster_module(src_proxyinstances)
            RedisCCTopoOperator(dst_cluster).transfer_instances_to_cluster_module(dst_proxyinstances)

        return True

    def dts_online_switch_update_nodes_domain(self):
        """
        dts在线切换,更新两个集群的nodes域名
        """
        src_cluster_id: int = self.cluster["src_cluster_id"]
        dst_cluster_id: int = self.cluster["dst_cluster_id"]
        for cluster_id in [src_cluster_id, dst_cluster_id]:
            cluster = Cluster.objects.get(id=cluster_id)
            cluster_entry = cluster.clusterentry_set.filter(role=ClusterEntryRole.NODE_ENTRY.value).first()
            nodes_domain = "nodes." + cluster.immute_domain
            dns_manage = DnsManage(bk_biz_id=cluster.bk_biz_id, bk_cloud_id=cluster.bk_cloud_id)
            if cluster_entry:
                # 该集群存在 nodes 域名的映射关系
                nodes_domain = cluster_entry.entry
                exists_insts = []
                for row in dns_manage.get_domain(domain_name=cluster_entry.entry):
                    exists_insts.append("{}#{}".format(row["ip"], row["port"]))
                # 先删除
                if exists_insts:
                    dns_manage.remove_domain_ip(domain=cluster_entry.entry, del_instance_list=exists_insts)
                # 再添加
                inst_ips = set()
                for row in cluster.storageinstance_set.all():
                    inst_ips.add(row.machine.ip)
                new_insts = [f"{ip}#{DEFAULT_REDIS_START_PORT}" for ip in inst_ips]
                dns_manage.create_domain(instance_list=new_insts, add_domain_name=nodes_domain)
            else:
                # 该集群不应该存在 nodes域名映射关系
                # 删除
                exists_insts = []
                for row in dns_manage.get_domain(domain_name=nodes_domain):
                    exists_insts.append("{}#{}".format(row["ip"], row["port"]))
                if exists_insts:
                    dns_manage.remove_domain_ip(domain=nodes_domain, del_instance_list=exists_insts)

    @transaction.atomic
    def redis_cluster_rename_domain(self):
        """
        重命名集群域名
        """
        cluster_id = self.cluster["cluster_id"]
        new_domain = self.cluster["new_domain"]
        new_name = new_domain.split(".")[-3]
        cluster = Cluster.objects.get(id=cluster_id)
        master_cluster_entry = ClusterEntry.objects.get(
            Q(cluster__id=cluster.id)
            & Q(cluster_entry_type=ClusterEntryType.DNS)
            & (Q(role=ClusterEntryRole.PROXY_ENTRY) | Q(role=ClusterEntryRole.MASTER_ENTRY)),
        )

        node_cluster_entry = ClusterEntry.objects.filter(
            Q(cluster__id=cluster.id)
            & Q(cluster_entry_type=ClusterEntryType.DNS)
            & Q(role=ClusterEntryRole.NODE_ENTRY),
        ).first()
        host_ids = set()
        for inst in cluster.proxyinstance_set.all():
            host_ids.add(inst.machine.bk_host_id)
        for inst in cluster.storageinstance_set.all():
            host_ids.add(inst.machine.bk_host_id)
        cc_manage = CcManage(cluster.bk_biz_id, cluster.cluster_type)
        cc_manage.recycle_host(list(host_ids))

        db_type = ClusterType.cluster_type_to_db_type(cluster.cluster_type)
        CcManage(cluster.bk_biz_id, cluster.cluster_type).delete_cluster_modules(db_type=db_type, cluster=cluster)

        cluster.immute_domain = new_domain
        cluster.name = new_name
        cluster.save(update_fields=["immute_domain", "name"])

        master_cluster_entry.entry = new_domain
        master_cluster_entry.save(update_fields=["entry"])

        if node_cluster_entry:
            node_cluster_entry.entry = "nodes." + new_domain
            node_cluster_entry.save(update_fields=["entry"])

        storageinstances = cluster.storageinstance_set.all()
        proxyinstances = cluster.proxyinstance_set.all()
        RedisCCTopoOperator(cluster).transfer_instances_to_cluster_module(storageinstances, is_increment=False)
        RedisCCTopoOperator(cluster).transfer_instances_to_cluster_module(proxyinstances, is_increment=False)

    def redis_cluster_version_update(self):
        """
        更新集群版本(major_version)
        """
        with atomic():
            for cluster_id in self.cluster["cluster_ids"]:
                cluster = Cluster.objects.get(id=cluster_id)
                cluster.major_version = self.cluster["db_version"]
                cluster.save(update_fields=["major_version"])
        return True

    @transaction.atomic
    def specifed_slots_migrate_record(self):
        """
        写入slot迁移记录
        """
        record = TbTendisSlotsMigrateRecord(
            creator=self.ticket_data["created_by"],
            related_slots_migrate_bill_id=self.ticket_data["uid"],
            bk_biz_id=self.ticket_data["bk_biz_id"],
            bk_cloud_id=self.cluster["bk_cloud_id"],
            cluster_type=self.cluster["cluster_type"],
            cluster_id=self.cluster["cluster_id"],
            cluster_name=self.cluster["cluster_name"],
            status=self.cluster["status"],
            migrate_specified_slot=self.cluster["migrate_specified_slot"],
        )
        record.save()

    @transaction.atomic
    def redis_rebalance_4_expansion(self):
        """
        写入slot迁移扩容记录
        """
        record = TbTendisSlotsMigrateRecord(
            creator=self.ticket_data["created_by"],
            related_slots_migrate_bill_id=self.ticket_data["uid"],
            bk_biz_id=self.ticket_data["bk_biz_id"],
            bk_cloud_id=self.cluster["bk_cloud_id"],
            cluster_type=self.cluster["cluster_type"],
            cluster_id=self.cluster["cluster_id"],
            cluster_name=self.cluster["cluster_name"],
            status=self.cluster["status"],
            old_instance_pair=self.cluster["old_instance_pair"],
            current_group_num=self.cluster["current_group_num"],
            target_group_num=self.cluster["target_group_num"],
            new_ip_group=self.cluster["new_ip_group"],
            specification=self.cluster["specification"],
            add_new_master_slave_pair=self.cluster["add_new_master_slave_pair"],
        )
        record.save()

    @transaction.atomic
    def redis_migrate_4_contraction(self):
        """
        写入slot迁移缩容记录
        """
        record = TbTendisSlotsMigrateRecord(
            creator=self.ticket_data["created_by"],
            related_slots_migrate_bill_id=self.ticket_data["uid"],
            bk_biz_id=self.ticket_data["bk_biz_id"],
            bk_cloud_id=self.cluster["bk_cloud_id"],
            cluster_type=self.cluster["cluster_type"],
            cluster_id=self.cluster["cluster_id"],
            cluster_name=self.cluster["cluster_name"],
            status=self.cluster["status"],
            old_instance_pair=self.cluster["old_instance_pair"],
            current_group_num=self.cluster["current_group_num"],
            target_group_num=self.cluster["target_group_num"],
            shutdown_master_slave_pair=self.cluster["shutdown_master_slave_pair"],
        )
        record.save()

    def update_nosql_dba(self):
        """
        更新dba
        """
        DBAdministratorHandler.upsert_biz_admins(self.ticket_data["bk_biz_id"], self.cluster["db_admins"])

    def storageinstance_bind_entry(self) -> bool:
        """
        机器上架元数据写入,这里只是单纯的上架，不会加入集群
        """
        machines = []
        proxies = []
        machine_type = self.cluster["machine_type"]
        for ip in self.cluster["new_proxy_ips"]:
            machines.append(
                {
                    "bk_biz_id": self.cluster["bk_biz_id"],
                    "ip": ip,
                    "machine_type": machine_type,
                    "spec_id": self.cluster["spec_id"],
                    "spec_config": self.cluster["spec_config"],
                }
            )
            proxies.append({"ip": ip, "port": self.cluster["port"]})

        with atomic():
            ins_status = InstanceStatus.RUNNING
            if self.cluster.get("ins_status"):
                ins_status = self.cluster["ins_status"]
            api.machine.create(
                machines=machines, creator=self.cluster["created_by"], bk_cloud_id=self.cluster["bk_cloud_id"]
            )
            api.proxy_instance.create(proxies=proxies, creator=self.cluster["created_by"], status=ins_status)
        return True

    def update_cluster_entry(self) -> bool:
        """
        更新nodes cluster_entry记录
        cluster_id/immute_domain
        bk_biz_id
        nodes_domain
        """
        nodes_domain = self.cluster["nodes_domain"]
        if "cluster_id" in self.cluster:
            cluster = Cluster.objects.get(id=self.cluster["cluster_id"], bk_biz_id=self.cluster["bk_biz_id"])
        elif "immute_domain" in self.cluster:
            cluster = Cluster.objects.get(
                immute_domain=self.cluster["immute_domain"], bk_biz_id=self.cluster["bk_biz_id"]
            )
        else:
            raise Exception("update_cluster_entry must have params[cluster_id/immute_domain]")
        cluster_entry = cluster.clusterentry_set.filter(role=ClusterEntryRole.NODE_ENTRY.value).first()
        storageinstances = cluster.storageinstance_set.all()

        if is_redis_cluster_protocal(cluster.cluster_type):
            if not cluster_entry:
                cluster_entry = ClusterEntry.objects.create(
                    cluster=cluster,
                    cluster_entry_type=ClusterEntryType.DNS,
                    entry=nodes_domain,
                    creator=cluster.creator,
                    role=ClusterEntryRole.NODE_ENTRY,
                )
                cluster_entry.storageinstance_set.add(*storageinstances)
                cluster_entry.save()
                logger.info(
                    _("redis集群:{} cluster_type:{} 新增 {} cluster_entry").format(
                        cluster.immute_domain, cluster.cluster_type, nodes_domain
                    )
                )
            else:
                # 应该存在的,确实存在,则更新
                cluster_entry.storageinstance_set.clear()
                cluster_entry.storageinstance_set.add(*storageinstances)
                cluster_entry.save()
                logger.info(
                    _("redis集群:{} cluster_type:{} 更新 cluster_entry:{}").format(
                        cluster.immute_domain, cluster.cluster_type, cluster_entry.entry
                    )
                )
        return True

    @transaction.atomic
    def swith_master_slave_for_cluster_faiover(self):
        """
        交换cluster集群的master和slave
        cluster["switch_master_slave_pairs"]={
            "cluster_id": 1,
            "replication_pairs": [
                {"master_ip": "a.a.a.a", "master_port": 30000, "slave_ip": "b.b.b.b", "slave_port": 30000},
                {"master_ip": "a.a.a.a", "master_port": 30001, "slave_ip": "b.b.b.b", "slave_port": 30001}
            ]
        }
        """
        switch_master_slave_pairs = self.cluster["switch_master_slave_pairs"]
        cluster = Cluster.objects.get(id=switch_master_slave_pairs["cluster_id"])
        cc_manage = CcManage(cluster.bk_biz_id, cluster.cluster_type)
        bk_host_ids = []
        for replication_pair in switch_master_slave_pairs["replication_pairs"]:
            master_ip = replication_pair["master_ip"]
            master_port = replication_pair["master_port"]
            slave_ip = replication_pair["slave_ip"]
            slave_port = replication_pair["slave_port"]

            master_obj = cluster.storageinstance_set.get(machine__ip=master_ip, port=master_port)
            if not master_obj:
                raise Exception(
                    _("cluster:{} master实例 {}:{} 不存在").format(cluster.immute_domain, master_ip, master_port)
                )

            slave_obj = cluster.storageinstance_set.get(machine__ip=slave_ip, port=slave_port)
            if not slave_obj:
                raise Exception(_("cluster:{} slave实例 {}:{} 不存在").format(cluster.immute_domain, slave_ip, slave_port))

            bk_host_ids.append(master_obj.machine.bk_host_id)
            bk_host_ids.append(slave_obj.machine.bk_host_id)

            new_master_obj = slave_obj
            new_master_obj.instance_role = InstanceRole.REDIS_MASTER
            new_master_obj.instance_inner_role = InstanceInnerRole.MASTER
            new_master_obj.cluster_type = cluster.cluster_type
            new_master_obj.save(update_fields=["instance_role", "instance_inner_role", "cluster_type"])

            new_slave_obj = master_obj
            new_slave_obj.instance_role = InstanceRole.REDIS_SLAVE
            new_slave_obj.instance_inner_role = InstanceInnerRole.SLAVE
            new_slave_obj.cluster_type = cluster.cluster_type
            new_slave_obj.save(update_fields=["instance_role", "instance_inner_role", "cluster_type"])

            StorageInstanceTuple.objects.filter(ejector=master_obj, receiver=slave_obj).update(
                ejector=new_master_obj, receiver=new_slave_obj
            )

            for proxy in cluster.proxyinstance_set.all():
                proxy.storageinstance.remove(master_obj)
                proxy.storageinstance.add(new_master_obj)
                proxy.save()
            # 切换新master服务实例角色标签
            cc_manage.add_label_for_service_instance(
                bk_instance_ids=[new_master_obj.bk_instance_id],
                labels_dict={"instance_role": InstanceRole.REDIS_MASTER.value},
            )
            # 切换新slave服务实例角色标签
            cc_manage.add_label_for_service_instance(
                bk_instance_ids=[new_slave_obj.bk_instance_id],
                labels_dict={"instance_role": InstanceRole.REDIS_SLAVE.value},
            )
        cc_manage.update_host_properties(bk_host_ids)
