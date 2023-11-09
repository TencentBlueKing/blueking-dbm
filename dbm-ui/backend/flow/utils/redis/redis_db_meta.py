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
from django.db.transaction import atomic
from django.utils.translation import ugettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta import api
from backend.db_meta.api.cluster.nosqlcomm.create_cluster import update_cluster_type
from backend.db_meta.api.cluster.tendiscache.handler import TendisCacheClusterHandler
from backend.db_meta.api.cluster.tendispluscluster.handler import TendisPlusClusterHandler
from backend.db_meta.api.cluster.tendisssd.handler import TendisSSDClusterHandler
from backend.db_meta.enums import (
    AccessLayer,
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
from backend.flow.consts import DEFAULT_DB_MODULE_ID, ConfigFileEnum, ConfigTypeEnum, InstanceStatus
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

    def proxy_status_update(self) -> bool:
        """
        proxy状态更新
        """
        api.proxy_instance.update(
            proxies=[
                {
                    "ip": self.cluster["ip"],
                    "port": self.cluster["port"],
                    "status": InstanceStatus.RUNNING.value
                    if self.ticket_data["ticket_type"] == TicketType.REDIS_OPEN
                    else InstanceStatus.UNAVAILABLE.value,
                }
            ]
        )
        return True

    def cluster_status_update(self) -> bool:
        cluster = Cluster.objects.get(id=self.cluster["cluster_id"])
        if self.ticket_data["ticket_type"] == TicketType.REDIS_CLOSE:
            cluster.phase = ClusterPhase.OFFLINE.value
        else:
            cluster.phase = ClusterPhase.ONLINE.value
        cluster.save()
        return True

    def redis_install(self) -> bool:
        """
        Redis实例上架、单机器级别。
        """
        machines, ins, cluster_type = [], [], ""
        if "cluster_type" in self.ticket_data:
            cluster_type = self.ticket_data["cluster_type"]
        else:
            cluster_type = self.cluster["cluster_type"]

        if cluster_type == ClusterType.TendisTwemproxyRedisInstance.value:
            machine_type = MachineType.TENDISCACHE.value
        elif cluster_type == ClusterType.TendisPredixyTendisplusCluster.value:
            machine_type = MachineType.TENDISPLUS.value
        elif cluster_type == ClusterType.TwemproxyTendisSSDInstance.value:
            machine_type = MachineType.TENDISSSD.value
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
            bk_cloud_id = 0
            ins_status = InstanceStatus.RUNNING
            if self.cluster.get("ins_status"):
                ins_status = self.cluster["ins_status"]
            if "bk_cloud_id" in self.ticket_data:
                bk_cloud_id = self.ticket_data["bk_cloud_id"]
            else:
                bk_cloud_id = self.cluster["bk_cloud_id"]
            api.machine.create(machines=machines, creator=self.ticket_data["created_by"], bk_cloud_id=bk_cloud_id)
            api.storage_instance.create(instances=ins, creator=self.ticket_data["created_by"], status=ins_status)
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

    def redis_make_cluster(self) -> bool:
        """
        建立集群关系
        """
        proxy_port = self.cluster["proxy_port"]
        proxies = [{"ip": proxy_ip, "port": proxy_port} for proxy_ip in self.cluster["new_proxy_ips"]]

        storages = []
        for server in self.cluster["servers"]:
            ip_port, _, seg_range, _ = server.split(SPACE_DIVIDER)
            ip, port = ip_port.split(IP_PORT_DIVIDER)
            storages.append({"ip": ip, "port": port, "seg_range": seg_range})
        if self.cluster["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance.value:
            TendisCacheClusterHandler.create(
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
                }
            )
        elif self.cluster["cluster_type"] == ClusterType.TwemproxyTendisSSDInstance.value:
            TendisSSDClusterHandler.create(
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
                }
            )

        return True

    def tendisplus_make_cluster(self) -> bool:
        """
        tendisplus建立集群关系
        """
        proxy_port = self.cluster["proxy_port"]
        proxies = [{"ip": proxy_ip, "port": proxy_port} for proxy_ip in self.cluster["new_proxy_ips"]]
        inst_num = self.cluster["inst_num"]
        master_start_port = self.cluster["start_port"]

        #  这里只传master
        storages = []
        for ip in self.cluster["new_master_ips"]:
            for n in range(0, inst_num):
                port = master_start_port + n
                storages.append({"ip": ip, "port": port})

        TendisPlusClusterHandler.create(
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
                StorageInstance.objects.filter(machine__ip=slave_info["ip"], port__in=slave_info["ports"]).update(
                    status=InstanceStatus.UNAVAILABLE
                )
                logger.info(
                    "update old_slave {} ports: {} status to UNAVAILABLE".format(slave_info["ip"], slave_info["ports"])
                )

            cluster = Cluster.objects.get(
                bk_cloud_id=self.cluster["bk_cloud_id"], immute_domain=self.cluster["immute_domain"]
            )
            api.cluster.nosqlcomm.redo_slaves(cluster, self.cluster["tendiss"], self.cluster["created_by"])
        return True

    def redis_replace_pair(self) -> bool:
        """
        创建主从关系， 然后在加入集群
        """
        with atomic():
            cluster = Cluster.objects.get(
                bk_cloud_id=self.cluster["bk_cloud_id"], immute_domain=self.cluster["immute_domain"]
            )
            tendiss, replic_tuple = [], []
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
                StorageInstance.objects.filter(
                    machine__ip=self.cluster["meta_update_ip"], port__in=self.cluster["meta_update_ports"]
                ).update(status=self.cluster["meta_update_status"])
        return True

    def instances_failover_4_scene(self) -> bool:
        """1.修改状态、2.切换角色"""
        self.instances_status_update()
        with atomic():
            for port in self.cluster["meta_update_ports"]:
                old_master = StorageInstance.objects.get(machine__ip=self.cluster["meta_update_ip"], port=port)
                old_slave = old_master.as_ejector.get().receiver
                StorageInstanceTuple.objects.get(ejector=old_master, receiver=old_slave).delete(keep_parents=True)
                StorageInstanceTuple.objects.create(ejector=old_slave, receiver=old_master)
                old_master.instance_role = InstanceRole.REDIS_SLAVE.value
                old_master.instance_inner_role = InstanceInnerRole.SLAVE.value
                old_master.save(update_fields=["instance_role", "instance_inner_role"])
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

        if self.cluster["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance.value:
            self.cluster["proxy_version"] = ConfigFileEnum.Twemproxy
        elif self.cluster["cluster_type"] == ClusterType.TwemproxyTendisSSDInstance.value:
            self.cluster["proxy_version"] = ConfigFileEnum.Twemproxy
        elif self.cluster["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster.value:
            self.cluster["proxy_version"] = ConfigFileEnum.Predixy
        proxy_config = self.__get_cluster_config(
            self.cluster["domain_name"],
            self.cluster["proxy_version"],
            ConfigTypeEnum.ProxyConf,
            self.cluster["cluster_type"],
        )

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
            temp_proxy_password=base64.b64encode(proxy_config["password"].encode("utf-8")),
            temp_cluster_proxy=self.cluster["temp_cluster_proxy"],
            prod_temp_instance_pairs=self.cluster["prod_temp_instance_pairs"],
            host_count=self.cluster["host_count"],
            recovery_time_point=self.cluster["recovery_time_point"],
            status=self.cluster["status"],
            temp_redis_password=base64.b64encode(proxy_config["redis_password"].encode("utf-8")),
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
        主从互切
                act_kwargs.cluster["role_swap_host"].append({"new_ejector":new_host_master,"new_receiver":old_master})
        """
        with atomic():
            for ins in self.cluster["role_swap_ins"]:
                ins1 = StorageInstance.objects.get(machine__ip=ins["new_receiver_ip"], port=ins["new_receiver_port"])
                ins2 = StorageInstance.objects.get(machine__ip=ins["new_ejector_ip"], port=ins["new_ejector_port"])

                # 修改 proxy backend
                temp_proxy_set = list(ins1.proxyinstance_set.all())
                ins1.proxyinstance_set.clear()
                ins1.proxyinstance_set.add(*ins2.proxyinstance_set.all())
                ins2.proxyinstance_set.clear()
                ins2.proxyinstance_set.add(*temp_proxy_set)
                # 变更同步关系
                StorageInstanceTuple.objects.get(ejector=ins1, receiver=ins2).delete(keep_parents=True)
                StorageInstanceTuple.objects.create(ejector=ins2, receiver=ins1)

                # 变更角色
                temp_instance_role = ins1.instance_role
                tmep_instance_inner_role = ins1.instance_inner_role

                ins1.instance_role = ins2.instance_role
                ins1.instance_inner_role = ins2.instance_inner_role

                ins2.instance_role = temp_instance_role
                ins2.instance_inner_role = tmep_instance_inner_role

                ins1.save(update_fields=["instance_role", "instance_inner_role"])
                ins2.save(update_fields=["instance_role", "instance_inner_role"])

        return True

    def add_clb_domain(self):
        """
        增加clb记录
        """
        entry_type = ClusterEntryType.CLB
        if self.cluster["clb_domain"] != "":
            entry_type = ClusterEntryType.CLBDNS
        cluster = Cluster.objects.get(
            bk_cloud_id=self.cluster["bk_cloud_id"], immute_domain=self.cluster["immute_domain"]
        )
        cluster_entry = ClusterEntry.objects.create(
            cluster=cluster,
            cluster_entry_type=entry_type,
            entry=self.cluster["ip"],
            creator=self.cluster["created_by"],
        )
        cluster_entry.save()
        clb_entry = CLBEntryDetail.objects.create(
            clb_ip=self.cluster["ip"],
            clb_id=self.cluster["id"],
            listener_id=self.cluster["listener_id"],
            clb_region=self.cluster["region"],
            entry_id=cluster_entry.id,
            creator=self.cluster["created_by"],
        )
        clb_entry.save()

    def add_polairs_domain(self):
        """
        增加polairs记录
        """
        cluster = Cluster.objects.get(
            bk_cloud_id=self.cluster["bk_cloud_id"], immute_domain=self.cluster["immute_domain"]
        )
        cluster_entry = ClusterEntry.objects.create(
            cluster=cluster,
            cluster_entry_type=ClusterEntryType.POLARIS,
            entry=self.cluster["name"],
            creator=self.cluster["created_by"],
        )
        cluster_entry.save()
        alias_token = ""
        if self.cluster.get("alias_token"):
            alias_token = self.cluster["alias_token"]
        polaris_entry = PolarisEntryDetail.objects.create(
            polaris_name=self.cluster["name"],
            polaris_l5=self.cluster["l5"],
            polaris_token=self.cluster["token"],
            alias_token=alias_token,
            entry_id=cluster_entry.id,
            creator=self.cluster["created_by"],
        )
        polaris_entry.save()

    def tendis_add_clb_domain_4_scene(self):
        """ 增加CLB 域名 """
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
        """ 主域名直接指向CLB """
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
        """ 主域名解绑CLB """
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

        return True

    def redis_cluster_version_update(self):
        """
        更新集群版本(major_version)
        """
        cluster = Cluster.objects.get(
            bk_cloud_id=self.cluster["bk_cloud_id"], immute_domain=self.cluster["immute_domain"]
        )
        cluster.major_version = self.cluster["target_version"]
        cluster.save(update_fields=["major_version"])
        return True
