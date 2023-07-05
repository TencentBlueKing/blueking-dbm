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
import logging
from typing import Any

from django.db import transaction
from django.db.transaction import atomic
from django.utils.translation import ugettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName, OpType, ReqType
from backend.db_meta import api
from backend.db_meta.api.cluster.tendiscache.handler import TendisCacheClusterHandler
from backend.db_meta.api.cluster.tendispluscluster.handler import TendisPlusClusterHandler
from backend.db_meta.api.cluster.tendisssd.handler import TendisSSDClusterHandler
from backend.db_meta.enums import ClusterPhase, ClusterType, InstanceInnerRole, InstanceRole, MachineType
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_services.dbbase.constants import IP_PORT_DIVIDER, SPACE_DIVIDER
from backend.db_services.redis.rollback.models import TbTendisRollbackTasks
from backend.flow.consts import DEFAULT_DB_MODULE_ID, ConfigFileEnum, ConfigTypeEnum, InstanceStatus
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
            api.machine.create(
                machines=machines, creator=self.cluster["created_by"], bk_cloud_id=self.cluster["bk_cloud_id"]
            )
            api.proxy_instance.create(
                proxies=proxies, creator=self.cluster["created_by"], status=InstanceStatus.RUNNING
            )
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
                for n in range(0, self.cluster["inst_num"]):
                    port = n + self.cluster["start_port"]
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
                for n in range(0, self.cluster["inst_num"]):
                    port = n + self.cluster["start_port"]
                    ins.append({"ip": ip, "port": port, "instance_role": InstanceRole.REDIS_SLAVE.value})

        with atomic():
            bk_cloud_id = 0
            if "bk_cloud_id" in self.ticket_data:
                bk_cloud_id = self.ticket_data["bk_cloud_id"]
            else:
                bk_cloud_id = self.cluster["bk_cloud_id"]
            api.machine.create(machines=machines, creator=self.ticket_data["created_by"], bk_cloud_id=bk_cloud_id)
            api.storage_instance.create(instances=ins, creator=self.ticket_data["created_by"])
        return True

    def replicaof(self) -> bool:
        """
        批量配置主从关系
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

    def redis_make_cluster(self) -> bool:
        """
        建立集群关系
        """
        proxy_port = self.ticket_data["proxy_port"]
        proxies = [{"ip": proxy_ip, "port": proxy_port} for proxy_ip in self.cluster["new_proxy_ips"]]

        storages = []
        for server in self.cluster["servers"]:
            ip_port, _, seg_range, _ = server.split(SPACE_DIVIDER)
            ip, port = ip_port.split(IP_PORT_DIVIDER)
            storages.append({"ip": ip, "port": port, "seg_range": seg_range})
        if self.ticket_data["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance.value:
            TendisCacheClusterHandler.create(
                **{
                    "bk_biz_id": self.ticket_data["bk_biz_id"],
                    "bk_cloud_id": self.ticket_data["bk_cloud_id"],
                    "name": self.ticket_data["cluster_name"],
                    "alias": self.ticket_data["cluster_alias"],
                    "major_version": self.ticket_data["db_version"],
                    "immute_domain": self.ticket_data["domain_name"],
                    "db_module_id": DEFAULT_DB_MODULE_ID,
                    "proxies": proxies,
                    "storages": storages,
                    "creator": self.ticket_data["created_by"],
                    "region": self.ticket_data.get("city_code"),
                }
            )
        elif self.ticket_data["cluster_type"] == ClusterType.TwemproxyTendisSSDInstance.value:
            TendisSSDClusterHandler.create(
                **{
                    "bk_biz_id": self.ticket_data["bk_biz_id"],
                    "bk_cloud_id": self.ticket_data["bk_cloud_id"],
                    "name": self.ticket_data["cluster_name"],
                    "alias": self.ticket_data["cluster_alias"],
                    "major_version": self.ticket_data["db_version"],
                    "immute_domain": self.ticket_data["domain_name"],
                    "db_module_id": DEFAULT_DB_MODULE_ID,
                    "proxies": proxies,
                    "storages": storages,
                    "creator": self.ticket_data["created_by"],
                    "region": self.ticket_data.get("city_code"),
                }
            )

        return True

    def tendisplus_make_cluster(self) -> bool:
        """
        tendisplus建立集群关系
        """
        proxy_port = self.ticket_data["proxy_port"]
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
                "bk_biz_id": self.ticket_data["bk_biz_id"],
                "bk_cloud_id": self.ticket_data["bk_cloud_id"],
                "name": self.ticket_data["cluster_name"],
                "alias": self.ticket_data["cluster_alias"],
                "major_version": self.ticket_data["db_version"],
                "immute_domain": self.ticket_data["domain_name"],
                "db_module_id": DEFAULT_DB_MODULE_ID,
                "proxies": proxies,
                "storages": storages,
                "creator": self.ticket_data["created_by"],
                "region": self.ticket_data.get("city_code"),
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
            api.cluster.nosqlcomm.decommission_instances(
                ip=self.cluster["ip"], bk_cloud_id=self.cluster["bk_cloud_id"], ports=self.cluster["ports"]
            )
        return True

    def tendis_switch_4_scene(self):
        """切换 nosql_set_dtl, 挪动CC 模块"""
        cluster = Cluster.objects.get(
            bk_cloud_id=self.cluster["bk_cloud_id"], immute_domain=self.cluster["immute_domain"]
        )
        api.cluster.nosqlcomm.switch_tendis(cluster=cluster, tendisss=self.cluster["sync_relation"])

    def update_rollback_task_status(self) -> bool:
        """
        更新构造记录为已销毁
        """
        task = TbTendisRollbackTasks.objects.filter(
            related_rollback_bill_id=self.cluster["related_rollback_bill_id"],
            bk_biz_id=self.cluster["bk_biz_id"],
            prod_cluster=self.cluster["prod_cluster"],
        ).update(is_destroyed=1)
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
            prod_cluster=self.cluster["prod_cluster"],
            prod_instance_range=self.cluster["prod_instance_range"],
            temp_cluster_type=self.cluster["temp_cluster_type"],
            temp_instance_range=self.cluster["temp_instance_range"],
            temp_password=base64.b64encode(proxy_config["password"].encode("utf-8")),
            temp_cluster_proxy=self.cluster["temp_cluster_proxy"],
            prod_temp_instance_pairs=self.cluster["prod_temp_instance_pairs"],
            host_count=self.cluster["host_count"],
            recovery_time_point=self.cluster["recovery_time_point"],
            status=self.cluster["status"],
        )
        task.save()
