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
import datetime
import hashlib
import logging
import re
import traceback
from typing import Dict, List, Tuple

from django.db import transaction
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service, StaticIntervalGenerator

import backend.flow.utils.redis.redis_context_dataclass as flow_context
from backend.components import DBConfigApi, DRSApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.enums import ClusterType, InstanceRole, InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_services.redis_dts.constants import DtsCopyType, DtsTaskType
from backend.db_services.redis_dts.models.tb_tendis_dts_job import TbTendisDTSJob
from backend.db_services.redis_dts.models.tb_tendis_dts_task import TbTendisDtsTask
from backend.db_services.redis_dts.util import (
    get_redis_type_by_cluster_type,
    is_predixy_proxy_type,
    is_redis_cluster_protocal,
    is_redis_instance_type,
    is_tendisplus_instance_type,
    is_tendisssd_instance_type,
    is_twemproxy_proxy_type,
)
from backend.flow.consts import DEFAULT_TENDISPLUS_KVSTORECOUNT, GB, MB, ConfigTypeEnum
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.redis.redis_cluster_nodes import (
    ClusterNodeData,
    decode_cluster_info,
    get_masters_with_slots,
    group_slaves_by_master_id,
)
from backend.flow.utils.redis.redis_context_dataclass import RedisDtsContext
from backend.flow.utils.redis.redis_proxy_util import decode_predixy_info_servers, decode_twemproxy_backends
from backend.flow.utils.redis.redis_util import domain_without_port

logger = logging.getLogger("flow")


class GetRedisDtsDataService(BaseService):
    """
    获取redis dts 相关数据,存入到上下文中
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        input_cluster = kwargs["cluster"]
        self.log_info("redis dts get data start,input_cluster....")
        self.log_info(input_cluster)
        dts_copy_type = global_data.get("dts_copy_type")
        trans_data.dts_copy_type = dts_copy_type
        trans_data.dts_bill_type = global_data.get("dts_bill_type")
        trans_data.bk_biz_id = global_data["bk_biz_id"]

        try:
            # 获取源集群信息
            if dts_copy_type == DtsCopyType.USER_BUILT_TO_DBM:
                trans_data.src_cluster_addr = input_cluster.get("src_cluster")
                trans_data.src_cluster_password = input_cluster.get("src_cluster_password")
                trans_data.src_cluster_type = input_cluster.get("src_cluster_type")

                # 无法确定源集群的bk_cloud_id,此时以目的集群的为准
                dst_cluster_data = self.get_cluster_info_by_domain(
                    global_data["bk_biz_id"], input_cluster["dst_cluster"]
                )
                trans_data.bk_cloud_id = dst_cluster_data["bk_cloud_id"]
                trans_data.src_cluster_region = dst_cluster_data["cluster_region"]
            if dts_copy_type == DtsCopyType.COPY_FROM_ROLLBACK_TEMP:
                pass
            else:
                src_cluster_data = self.get_cluster_info_by_domain(
                    global_data["bk_biz_id"], input_cluster["src_cluster"]
                )
                trans_data.bk_cloud_id = src_cluster_data["bk_cloud_id"]
                trans_data.src_cluster_id = src_cluster_data["cluster_id"]
                trans_data.src_cluster_addr = (
                    src_cluster_data["cluster_domain"] + ":" + str(src_cluster_data["cluster_port"])
                )
                trans_data.src_cluster_password = src_cluster_data["cluster_password"]
                trans_data.src_cluster_type = src_cluster_data["cluster_type"]
                trans_data.src_cluster_region = src_cluster_data["cluster_region"]
                trans_data.src_redis_password = src_cluster_data["redis_password"]
                self.log_info("src_cluster_data....{}".format(src_cluster_data))

                src_redis_data = self.get_cluster_slaves_data(
                    global_data["bk_biz_id"], src_cluster_data["cluster_domain"]
                )
                trans_data.src_cluster_running_master = src_redis_data[0]
                trans_data.src_slave_instances = src_redis_data[1]
                trans_data.src_slave_hosts = src_redis_data[2]
                trans_data.src_slave_instances = self.get_redis_slaves_data_size(trans_data)

            # 获取目的集群信息
            if dts_copy_type == DtsCopyType.COPY_TO_OTHER_SYSTEM:
                trans_data.dst_cluster_addr = input_cluster.get("dst_cluster")
                trans_data.dst_cluster_password = input_cluster.get("dst_cluster_password")
            else:
                dst_cluster_data = self.get_cluster_info_by_domain(
                    input_cluster["dst_bk_biz_id"], input_cluster["dst_cluster"]
                )
                trans_data.dst_cluster_id = dst_cluster_data["cluster_id"]
                trans_data.dst_cluster_addr = (
                    dst_cluster_data["cluster_domain"] + ":" + str(dst_cluster_data["cluster_port"])
                )
                trans_data.dst_cluster_password = dst_cluster_data["cluster_password"]
                trans_data.dst_cluster_type = dst_cluster_data["cluster_type"]
                trans_data.dst_redis_password = dst_cluster_data["redis_password"]
        except Exception as e:
            traceback.print_exc()
            self.log_error("get redis dts data failed:{}".format(e))
            return False

        # 迁移正则
        trans_data.key_white_regex = input_cluster.get("key_white_regex")
        trans_data.key_black_regex = input_cluster.get("key_black_regex")

        self.log_info("redis dts get data successfully")
        data.outputs["trans_data"] = trans_data
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", requiredc=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    @staticmethod
    def get_cluster_info_by_domain(
        bk_biz_id: int,
        cluster_domain: str,
    ) -> dict:
        """
        根据域名获取集群信息(id,类型等)
        """
        try:
            cluster_domain = domain_without_port(cluster_domain)
            cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
            one_master = cluster.storageinstance_set.filter(
                instance_role=InstanceRole.REDIS_MASTER.value, status=InstanceStatus.RUNNING
            ).first()
            proxy_conf = DBConfigApi.query_conf_item(
                params={
                    "bk_biz_id": str(cluster.bk_biz_id),
                    "level_name": LevelName.CLUSTER.value,
                    "level_value": cluster.immute_domain,
                    "level_info": {"module": str(cluster.db_module_id)},
                    "conf_file": cluster.proxy_version,
                    "conf_type": ConfigTypeEnum.ProxyConf,
                    "namespace": cluster.cluster_type,
                    "format": FormatType.MAP,
                }
            )
            proxy_content = proxy_conf.get("content", {})

            redis_conf = DBConfigApi.query_conf_item(
                params={
                    "bk_biz_id": str(cluster.bk_biz_id),
                    "level_name": LevelName.CLUSTER.value,
                    "level_value": cluster.immute_domain,
                    "level_info": {"module": str(cluster.db_module_id)},
                    "conf_file": cluster.major_version,
                    "conf_type": ConfigTypeEnum.DBConf,
                    "namespace": cluster.cluster_type,
                    "format": FormatType.MAP,
                }
            )
            redis_content = redis_conf.get("content", {})

            return {
                "cluster_id": cluster.id,
                "bk_cloud_id": cluster.bk_cloud_id,
                "cluster_domain": cluster.immute_domain,
                "cluster_type": cluster.cluster_type,
                "cluster_password": proxy_content.get("password"),
                "cluster_port": proxy_content.get("port"),
                "cluster_version": cluster.major_version,
                "cluster_name": cluster.name,
                "cluster_region": one_master.machine.bk_city.bk_idc_city_name,
                "redis_password": redis_content.get("requirepass"),
            }
        except Exception as e:
            traceback.print_exc()
            logger.error(f"get cluster info by domain failed {e}, cluster_domain: {cluster_domain}")
            raise Exception(f"get cluster info by domain failed {e}, cluster_domain: {cluster_domain}")

    @staticmethod
    def get_cluster_slaves_data(bk_biz_id: int, cluster_domain: str) -> Tuple[dict, list, list]:
        """
        获取集群下的slaves实例信息
        """
        try:
            cluster_domain = domain_without_port(cluster_domain)
            cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
            one_master_instance = cluster.storageinstance_set.filter(
                instance_role=InstanceRole.REDIS_MASTER.value, status=InstanceStatus.RUNNING
            ).first()
            running_master = {
                "ip": one_master_instance.machine.ip,
                "port": one_master_instance.port,
                "status": one_master_instance.status,
                "instance_role": one_master_instance.instance_role,
            }
            slave_instances = []
            uniq_hosts = set()
            slave_hosts = []
            kvstore: int = 0
            for slave in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_SLAVE.value):
                if is_tendisplus_instance_type(cluster.cluster_type):
                    kvstore = DEFAULT_TENDISPLUS_KVSTORECOUNT
                else:
                    kvstore = 1
                slave_instances.append(
                    {
                        "ip": slave.machine.ip,
                        "port": slave.port,
                        "db_type": get_redis_type_by_cluster_type(cluster.cluster_type),
                        "status": slave.status,
                        "data_size": 1 * 1024 * 1024 * 1024,
                        "kvstorecount": kvstore,
                        "segment_start": -1,
                        "segment_end": -1,
                    }
                )
                if slave.machine.ip in uniq_hosts:
                    continue
                uniq_hosts.add(slave.machine.ip)
                slave_hosts.append(
                    {
                        "ip": slave.machine.ip,
                        "mem_info": {},
                        "disk_info": {},
                    }
                )
            return running_master, slave_instances, slave_hosts
        except Exception as e:
            logger.error(f"get cluster redis instances data failed {e}, cluster_domain: {cluster_domain}")
            raise Exception(f"get cluster redis instances data failed {e}, cluster_domain: {cluster_domain}")

    @staticmethod
    def decode_info_cmd(info_str: str) -> Dict:
        info_ret: Dict[str, dict] = {}
        info_list: List = info_str.split("\n")
        for info_item in info_list:
            info_item = info_item.strip()
            if info_item.startswith("#"):
                continue
            if len(info_item) == 0:
                continue
            tmp_list = info_item.split(":", 1)
            if len(tmp_list) < 2:
                continue
            tmp_list[0] = tmp_list[0].strip()
            tmp_list[1] = tmp_list[1].strip()
            info_ret[tmp_list[0]] = tmp_list[1]
        return info_ret

    def get_redis_slaves_data_size(self, trans_data: RedisDtsContext) -> list:
        """
        获取redis slave的数据大小
        """
        info_cmd: str = ""
        if is_redis_instance_type(trans_data.src_cluster_type):
            info_cmd = "info memory"
        elif is_tendisplus_instance_type(trans_data.src_cluster_type):
            info_cmd = "info Dataset"
        elif is_tendisssd_instance_type(trans_data.src_cluster_type):
            info_cmd = "info"
        slave_addrs = [slave["ip"] + ":" + str(slave["port"]) for slave in trans_data.src_slave_instances]
        resp = DRSApi.redis_rpc(
            {
                "addresses": slave_addrs,
                "db_num": 0,
                "password": trans_data.src_redis_password,
                "command": info_cmd,
                "bk_cloud_id": trans_data.bk_cloud_id,
            }
        )
        info_ret: Dict[str, Dict] = {}
        for item in resp:
            info_ret[item["address"]] = self.decode_info_cmd(item["result"])
        new_slave_instances: List = []
        for slave in trans_data.src_slave_instances:
            slave_addr = slave["ip"] + ":" + str(slave["port"])
            if slave["db_type"] == ClusterType.TendisRedisInstance.value:
                slave["data_size"] = int(info_ret[slave_addr]["used_memory"])
            elif slave["db_type"] == ClusterType.TendisTendisplusInsance.value:
                slave["data_size"] = int(info_ret[slave_addr]["rocksdb.total-sst-files-size"])
            elif slave["db_type"] == ClusterType.TendisTendisSSDInstance.value:
                rockdb_size = 0
                level_head_reg = re.compile(r"^level-\d+$")
                level_data_reg = re.compile(r"^bytes=(\d+),num_entries=(\d+),num_deletions=(\d+)")
                for k, v in info_ret[slave_addr].items():
                    if level_head_reg.match(k):
                        tmp_list = level_data_reg.findall(v)
                        if len(tmp_list) != 1:
                            err = f"redis:{slave_addr} info 'RocksDB Level stats' format not correct,{k}:{v}"
                            self.log_error(err)
                            raise Exception(err)
                        size01 = int(tmp_list[0][0])
                        rockdb_size += size01
                slave["data_size"] = rockdb_size
            new_slave_instances.append(slave)
        return new_slave_instances


class GetRedisDtsDataComponent(Component):
    name = __name__
    code = "get_redis_dts_data"
    bound_service = GetRedisDtsDataService


class RedisDtsPrecheckService(BaseService):
    """
    redis dts前置检查
    """

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data: RedisDtsContext = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        # 打印信息
        self.log_info(" RedisDtsPrecheckService start")
        try:
            # 所有slave必须是running状态且可连接
            if not self.check_all_src_slaves_running(trans_data):
                return False
            # 源slave磁盘空间是否足够
            if not self.check_src_redis_host_disk(trans_data):
                return False
            # 源集群如果是cluster协议,则检查集群状态是否ok
            if not self.check_src_cluster_state_ok(trans_data):
                return False
            # 源集群如果是cluster协议,则检查集群节点是否正常
            self.log_info("start check_src_cluster_nodes_ok")
            cluster_nice_slaves = self.check_src_cluster_nodes_ok(trans_data)
            if not cluster_nice_slaves and len(cluster_nice_slaves) > 0:
                trans_data.src_slave_instances = cluster_nice_slaves
            # 目的集群可连接性
            if not self.check_dst_cluster_connected(trans_data):
                return False
        except Exception as e:
            traceback.print_exc()
            self.log_error("redis dts precheck failed:{}".format(e))
            return False
        self.log_info("redis dts precheck success")
        data.outputs["trans_data"] = trans_data
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", requiredc=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def check_all_src_slaves_running(self, trans_data: RedisDtsContext) -> bool:
        """
        检查所有源redis slave是否都是running状态
        """
        unrunning_slave_cnt = 0
        for slave in trans_data.src_slave_instances:
            if slave["status"] != InstanceStatus.RUNNING.value:
                unrunning_slave_cnt += 1
        if unrunning_slave_cnt > 0:
            self.log_error(
                _("源redis集群{}存在{}个非running状态的slave".format(trans_data.src_cluster_addr, unrunning_slave_cnt))
            )
            return False
        slaves_addr = [slave["ip"] + ":" + str(slave["port"]) for slave in trans_data.src_slave_instances]
        DRSApi.redis_rpc(
            {
                "addresses": slaves_addr,
                "db_num": 0,
                "password": trans_data.src_redis_password,
                "command": "ping",
                "bk_cloud_id": trans_data.bk_cloud_id,
            }
        )
        return True

    @staticmethod
    def decode_slave_host_disk_info(disk_line: str) -> dict:
        """
        解析slave磁盘信息
        如: /dev/vdb       103080888 1788160  96033464   2% /data
        """
        l01 = disk_line.split()
        ret = {}
        ret["filesystem"] = l01[0]
        ret["total"] = int(l01[1]) * 1024
        ret["used"] = int(l01[2]) * 1024
        ret["avail"] = int(l01[3]) * 1024
        ret["used_ratio"] = int(l01[4].replace("%", ""))
        ret["mount_on"] = l01[5]
        return ret

    def check_src_redis_host_disk(self, trans_data: RedisDtsContext) -> bool:
        """
        检查源redis磁盘空间是否足够
        """
        disk_used = trans_data.disk_used
        for src_slave in trans_data.src_slave_instances:
            disk_str = disk_used.get(src_slave["ip"])["data"]
            disk_info = self.decode_slave_host_disk_info(disk_str)
            if disk_info["used_ratio"] > 90:
                self.log_error(
                    "source redis:{} {} disk_used:{}% > 90%".format(
                        src_slave["ip"], disk_info["filesystem"], disk_info["used_ratio"]
                    )
                )
                return False
            if (disk_info["used"] + src_slave["data_size"]) / disk_info["total"] > 0.9:
                self.log_error(
                    "source redis:{} {} disk_used:{}+redis_data_size:{} will >=90%".format(
                        src_slave["ip"] + ":" + str(src_slave["port"]),
                        disk_info["filesystem"],
                        disk_info["used"],
                        src_slave["data_size"],
                    )
                )
                return False
        slave_hosts = set(host["ip"] for host in trans_data.src_slave_instances)
        self.log_info(_("所有源redis slave机器:{} 磁盘空间检查通过").format(slave_hosts))
        return True

    def check_src_cluster_nodes_ok(self, trans_data: RedisDtsContext) -> List[dict]:
        """
        如果源集群是redis cluster协议,检查源集群节点是否正常:
        1. 每个负责slot的master都至少有一个running的slave
        2. 如果有多个running slave,则选择其中一个作为迁移节点
        """
        if not is_redis_cluster_protocal(trans_data.src_cluster_type):
            self.log_info(
                _("src_cluster:{} type:{} 无需检查cluster nodes是否ok").format(
                    trans_data.src_cluster_addr, trans_data.src_cluster_type
                )
            )
            return True
        # 获取集群cluster nodes信息
        running_master = trans_data.src_cluster_running_master
        master_addr = running_master["ip"] + ":" + str(running_master["port"])
        resp = DRSApi.redis_rpc(
            {
                "addresses": [master_addr],
                "db_num": 0,
                "password": trans_data.src_redis_password,
                "command": "cluster nodes",
                "bk_cloud_id": trans_data.bk_cloud_id,
            }
        )
        cluster_nodes_str = resp[0]["result"]
        self.log_info("src_cluster:{} cluster_nodes_str:\n {}".format(trans_data.src_cluster_addr, cluster_nodes_str))
        # 确保所有负责slots的master都至少有一个running的slave
        # 如果有多个running slave,则选择其中一个保存到nice_slaves中
        masters_with_slots = get_masters_with_slots(cluster_nodes_str)
        if len(masters_with_slots) == 0:
            self.log_error(
                "src_cluster:{} not found masters(with_slots),master:{}".format(
                    trans_data.src_cluster_addr, master_addr
                )
            )
            raise Exception(
                "src_cluster:{} not found masters(with_slots),master:{}".format(
                    trans_data.src_cluster_addr, master_addr
                )
            )
        slaves_by_masterid = group_slaves_by_master_id(cluster_nodes_str)
        meta_slaves = {}
        for src_slave in trans_data.src_slave_instances:
            addr = src_slave["ip"] + ":" + str(src_slave["port"])
            meta_slaves[addr] = src_slave
        nice_slaves = []
        for master in masters_with_slots:
            if master.node_id not in slaves_by_masterid:
                raise Exception("master {} has no slave".format(master.addr))
            slaves = slaves_by_masterid[master.node_id]
            one_running_slave: ClusterNodeData = None
            for slave in slaves:
                if slave.is_running() and (slave.addr in meta_slaves):
                    # slave 必须是running状态,并且在db_meta中存在
                    one_running_slave = slave
                    break
            if one_running_slave is None:
                raise Exception("master {} has no running slave".format(master.addr))
            nice_slaves.append(meta_slaves[one_running_slave.addr])
        self.log_info("check_src_cluster_nodes_ok nice_slaves:{}".format(nice_slaves))
        return nice_slaves

    def check_src_cluster_state_ok(self, trans_data: RedisDtsContext) -> bool:
        """
        如果源集群是redis cluster协议,检查源集群cluster_state是ok的
        """
        if not is_redis_cluster_protocal(trans_data.src_cluster_type):
            self.log_info(
                _(
                    "src_cluster:{} 类型是:{} 无需检查cluster state".format(
                        trans_data.src_cluster_addr, trans_data.src_cluster_type
                    )
                )
            )
            return True
        running_master = trans_data.src_cluster_running_master
        master_addr = running_master["ip"] + ":" + str(running_master["port"])
        resp = DRSApi.redis_rpc(
            {
                "addresses": [master_addr],
                "db_num": 0,
                "password": trans_data.src_redis_password,
                "command": "cluster info",
                "bk_cloud_id": trans_data.bk_cloud_id,
            }
        )
        cluster_info_str = resp[0]["result"]
        cluster_info = decode_cluster_info(cluster_info_str)
        if cluster_info.cluster_state != "ok":
            self.log_error(
                "src cluster:{} cluster_state:{} is not ok".format(
                    trans_data.src_cluster_addr, cluster_info.cluster_state
                )
            )
            # raise Exception(
            #     "src cluster:{} cluster_state:{} is not ok".format(
            #         trans_data.src_cluster_addr, cluster_info.cluster_state
            #     )
            # )
            return False
        self.log_info(
            "src_cluster:{} cluster_state:{}".format(trans_data.src_cluster_addr, cluster_info.cluster_state)
        )
        return True

    def check_dst_cluster_connected(self, trans_data: RedisDtsContext) -> bool:
        """
        检查目的集群是否可连接
        """
        # TODO 现在域名无法使用,目的集群先用 proxy_ip:proxy_port 代替
        cluster = Cluster.objects.get(bk_biz_id=trans_data.bk_biz_id, id=trans_data.dst_cluster_id)
        dst_proxy_addrs = []
        for proxy in cluster.proxyinstance_set.all():
            dst_proxy_addrs.append(proxy.machine.ip + ":" + str(proxy.port))
        DRSApi.redis_rpc(
            {
                "addresses": dst_proxy_addrs,
                "db_num": 0,
                "password": trans_data.dst_cluster_password,
                "command": "get a",
                "bk_cloud_id": trans_data.bk_cloud_id,
            }
        )
        self.log_info("dst_cluster:{} connect success".format(trans_data.dst_cluster_addr))
        return True


class RedisDtsPrecheckComponent(Component):
    name = __name__
    code = "redis_dts_precheck"
    bound_service = RedisDtsPrecheckService


class RedisDtsExecuteService(BaseService):
    """
    redis dts执行
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(10)

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data: RedisDtsContext = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        if trans_data.job_id and trans_data.task_ids:
            """如果job_id和task_ids已经存在,则表示已经执行过了,无需重复插入"""
            return True
        input_cluster = kwargs["cluster"]
        try:
            job_id: int = 0
            task_ids: list = []
            # root_id = kwargs["root_id"]
            uid = int(global_data["uid"])
            with transaction.atomic():
                job = TbTendisDTSJob()
                job.bill_id = uid
                job.app = trans_data.bk_biz_id
                job.bk_cloud_id = trans_data.bk_cloud_id
                job.user = global_data["created_by"]
                job.dts_bill_type = trans_data.dts_bill_type
                job.dts_copy_type = trans_data.dts_copy_type
                job.online_switch_type = global_data["online_switch_type"]
                job.datacheck = int(global_data["datacheck"])
                job.datarepair = int(global_data["datarepair"])
                job.datarepair_mode = global_data["datarepair_mode"]
                job.src_cluster = trans_data.src_cluster_addr
                job.src_cluster_type = trans_data.src_cluster_type

                job.src_rollback_bill_id = input_cluster["src_rollback_bill_id"]

                job.dst_bk_biz_id = input_cluster["dst_bk_biz_id"]
                job.dst_cluster = trans_data.dst_cluster_addr
                job.dst_cluster_type = trans_data.dst_cluster_type
                job.key_white_regex = trans_data.key_white_regex.encode("utf-8")
                job.key_black_regex = trans_data.key_black_regex.encode("utf-8")
                job.create_time = datetime.datetime.now()
                job.save()
                job_id = job.id

                src_password_base64 = base64.b64encode(trans_data.src_redis_password.encode("utf-8")).decode("utf-8")
                dst_passsword_base64 = base64.b64encode(trans_data.dst_cluster_password.encode("utf-8")).decode(
                    "utf-8"
                )
                cuncurrency_limit = self.get_src_redis_host_concurrency(trans_data)
                for slave in trans_data.src_slave_instances:
                    addr = slave["ip"] + ":" + str(slave["port"])
                    for kvstoreid in range(slave["kvstorecount"]):
                        task = TbTendisDtsTask()
                        task.bill_id = job.bill_id
                        task.user = job.user
                        task.app = job.app
                        task.bk_cloud_id = job.bk_cloud_id
                        task.dts_server = "1.1.1.1"
                        task.src_cluster = job.src_cluster
                        task.src_cluster_priority = 0
                        task.src_ip = slave["ip"]
                        task.src_port = slave["port"]
                        task.src_password = src_password_base64
                        task.src_dbtype = slave["db_type"]
                        task.src_dbsize = slave["data_size"]
                        task.src_seg_start = slave["segment_start"]
                        task.src_seg_end = slave["segment_end"]
                        task.src_weight = int(slave["port"] % 8)
                        task.src_ip_concurrency_limit = cuncurrency_limit
                        task.src_ip_zonename = trans_data.src_cluster_region
                        task.src_kvstore_id = kvstoreid
                        task.key_white_regex = trans_data.key_white_regex.encode("utf-8")
                        task.key_black_regex = trans_data.key_black_regex.encode("utf-8")
                        task.dst_cluster = job.dst_cluster
                        task.dst_password = dst_passsword_base64
                        task.create_time = datetime.datetime.now()
                        task.save()
                        task_ids.append(task.id)
        except Exception as e:
            traceback.print_exc()
            self.log_error("redis dts execute failed:{}".format(e))
            return False
        self.log_info("redis dts execute success")
        trans_data.job_id = job_id
        trans_data.task_ids = task_ids
        data.outputs["trans_data"] = trans_data
        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data: RedisDtsContext = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()
        task_ids = trans_data.task_ids
        tasks_rows = TbTendisDtsTask.objects.filter(id__in=task_ids)
        if self.__is_any_task_fail(tasks_rows):
            self.log_error(
                _(
                    "bill_id:{} src_cluster:{} dst_cluster:{} 某些tasks迁移失败".format(
                        tasks_rows[0].bill_id, tasks_rows[0].src_cluster, tasks_rows[0].dst_cluster
                    )
                )
            )
            return False
        if self.__is_all_tasks_success(tasks_rows):
            self.log_info(
                _(
                    "bill_id:{} src_cluster:{} dst_cluster:{} 所有tasks都成功且终止了迁移进程".format(
                        tasks_rows[0].bill_id, tasks_rows[0].src_cluster, tasks_rows[0].dst_cluster
                    )
                )
            )
            self.finish_schedule()
            return True
        if self.__is_all_tasks_incr_sync(tasks_rows):
            self.log_info(
                _(
                    "bill_id:{} src_cluster:{} dst_cluster:{} 所有tasks都是增量同步".format(
                        tasks_rows[0].bill_id, tasks_rows[0].src_cluster, tasks_rows[0].dst_cluster
                    )
                )
            )
            self.finish_schedule()
            return True
        # 继续下次循环
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", requiredc=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def get_src_redis_host_concurrency(self, trans_data: RedisDtsContext) -> int:
        """
        获取源redis host上可支持的并发度,对tendisSSD尤为重要,否则容易把磁盘打爆
        """
        max_datasize_instance: dict = None
        for slave in trans_data.src_slave_instances:
            if max_datasize_instance is None:
                max_datasize_instance = slave
                continue
            if max_datasize_instance["data_size"] < slave["data_size"]:
                max_datasize_instance = slave
        if trans_data.dts_copy_type == DtsCopyType.USER_BUILT_TO_DBM:
            return 5
        if max_datasize_instance["db_type"] == ClusterType.TendisTendisplusInsance:
            return 10

        if max_datasize_instance["data_size"] == 0:
            return 5

        self.log_info("get_src_redis_host_concurrency max_datasize_instance:{}".format(max_datasize_instance))
        if max_datasize_instance["db_type"] == ClusterType.TendisRedisInstance:
            max_size = 40 * GB
            if max_datasize_instance["data_size"] > max_size:
                return 1
            else:
                concurrency: int = max_size / max_datasize_instance["data_size"]
                if concurrency > 5:
                    return 5
                return concurrency
        if max_datasize_instance["db_type"] == ClusterType.TendisTendisSSDInstance:
            max_size = 200 * GB
            self.log_info("yes it's tendisSSD")
            if max_datasize_instance["data_size"] > max_size:
                return 1
            else:
                disk_used = trans_data.disk_used
                disk_str = disk_used.get(max_datasize_instance["ip"])["data"]
                disk_info = RedisDtsPrecheckService.decode_slave_host_disk_info(disk_str)
                max_avail_size = disk_info["total"] * 9 / 10 - disk_info["used"]
                concurrency: int = max_avail_size / max_datasize_instance["data_size"]
                self.log_info(
                    "get_src_redis_host_concurrency tendisSSD "
                    "max_avail_size:{} max_datasize_instance.data_size:{} concurrency{}".format(
                        max_avail_size, max_datasize_instance["data_size"], concurrency
                    )
                )
                if concurrency == 0:
                    self.log_error(
                        "{} total_size:{}MB used_size:{} max_avail_size:{}MB,data_size:{}MB".format(
                            max_datasize_instance["ip"],
                            disk_info["total"] / MB,
                            disk_info["used"] / MB,
                            max_avail_size / MB,
                            max_datasize_instance["data_size"] / MB,
                        )
                    )
                if concurrency > 5:
                    return 5
                return concurrency

    def __is_any_task_fail(self, tasks: List[TbTendisDtsTask]) -> bool:
        """
        判断是否有任务失败
        """
        for task in tasks:
            if task.status < 0:
                self.log_error(_("task:{} {}:{} 迁移失败".format(task.id, task.src_ip, task.src_port)))
                return True
        return False

    def __is_all_tasks_success(self, tasks: List[TbTendisDtsTask]) -> bool:
        """
        判断是否所有任务都成功
        """
        for task in tasks:
            if task.status != 2:
                return False
        return True

    def __is_all_tasks_incr_sync(self, tasks: List[TbTendisDtsTask]) -> bool:
        """
        判断是否所有任务都在增量同步中
        """
        for task in tasks:
            if task.status != 1:
                return False
            if task.src_dbtype == ClusterType.TendisTendisSSDInstance.value and task.task_type not in [
                DtsTaskType.TENDISSSD_MAKESYNC.value,
                DtsTaskType.TENDISSSD_WATCHOLDSYNC.value,
            ]:
                return False
            if task.src_dbtype == ClusterType.TendisRedisInstance.value and task.task_type not in [
                DtsTaskType.WATCH_CACHE_SYNC.value
            ]:
                return False
            if task.src_dbtype == ClusterType.TendisTendisplusInsance.value and task.task_type not in [
                DtsTaskType.TENDISPLUS_SENDINCR.value
            ]:
                return False
        return True


class RedisDtsExecuteComponent(Component):
    name = __name__
    code = "redis_dts_execute"
    bound_service = RedisDtsExecuteService


class RedisDtsOnlineSwitchPrecheck(BaseService):
    """
    redis dts在线切换前置检查
    """

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data: RedisDtsContext = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()
        try:
            # 检查源集群所有proxy节点状态是否正常
            src_proxy_instances = self.get_cluster_proxy_instances(trans_data.bk_biz_id, trans_data.src_cluster_id)
            trans_data.src_proxy_instances = src_proxy_instances
            not_running_proxys_cnt = 0
            for proxy in src_proxy_instances:
                if proxy["status"] != InstanceStatus.RUNNING.value:
                    not_running_proxys_cnt += 1
            if not_running_proxys_cnt > 0:
                self.log_error(
                    _("{}中有{}个proxy不是running状态".format(trans_data.src_cluster_addr, not_running_proxys_cnt))
                )
                return False
            # 检查源集群所有proxy节点的backend是否一致
            self.__check_twemproxy_backends(trans_data)
            self.__check_predixy_servers(trans_data)
        except Exception as e:
            logger.error(f"redis dts online switch precheck failed {e}")
            return False

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", requiredc=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    @staticmethod
    def get_cluster_proxy_instances(bk_biz_id: int, cluster_id: int) -> list:
        """
        获取集群下的proxy实例信息
        """
        try:
            cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
            proxy_instances = []
            for proxy in cluster.proxyinstance_set.all():
                proxy_instances.append(
                    {
                        "ip": proxy.machine.ip,
                        "port": proxy.port,
                        "admin_port": proxy.admin_port,
                        "status": proxy.status,
                    }
                )
            return proxy_instances
        except Exception as e:
            logger.error(f"get cluster proxy instances failed {e}, cluster_id: {cluster_id}")
            raise Exception(f"get cluster proxy instances failed {e}, cluster_id: {cluster_id}")

    def __check_twemproxy_backends(self, trans_data: RedisDtsContext):
        """
        检查twemproxy的backends是否一致
        """
        if not is_twemproxy_proxy_type(trans_data.src_cluster_type):
            return
        proxy_addrs = [ele["ip"] + ":" + str(ele["admin_port"]) for ele in trans_data.src_proxy_instances]
        resp = DRSApi.twemproxy_rpc(
            {
                "addresses": proxy_addrs,
                "db_num": 0,
                "password": "",
                "command": "get nosqlproxy servers",
                "bk_cloud_id": trans_data.bk_cloud_id,
            }
        )
        proxys_backend_md5 = []
        for ele in resp:
            backends_ret, _ = decode_twemproxy_backends(ele["result"])
            sorted_backends = sorted(backends_ret, key=lambda x: x.segment_start)
            sorted_str = ""
            for bck in sorted_backends:
                sorted_str += bck.string_without_app() + "\n"
            # 求sorted_str的md5值
            md5 = hashlib.md5(sorted_str.encode("utf-8")).hexdigest()
            proxys_backend_md5.append(
                {
                    "proxy_addr": ele["address"],
                    "backend_md5": md5,
                }
            )
        # 检查md5是否一致
        sorted_md5 = sorted(proxys_backend_md5, key=lambda x: x["backend_md5"])
        if sorted_md5[0]["backend_md5"] != sorted_md5[-1]["backend_md5"]:
            self.log_error(
                "twemproxy[{}->{}] backends is not same".format(
                    sorted_md5[0]["proxy_addr"], sorted_md5[-1]["proxy_addr"]
                )
            )
            raise Exception(
                "twemproxy[{}->{}] backends is not same".format(
                    sorted_md5[0]["proxy_addr"], sorted_md5[-1]["proxy_addr"]
                )
            )

    def __check_predixy_servers(self, trans_data: RedisDtsContext):
        """
        检查predixy的servers是否一致
        """
        if not is_predixy_proxy_type(trans_data.src_cluster_type):
            return
        proxy_addrs = [ele["ip"] + ":" + str(ele["admin_port"]) for ele in trans_data.src_proxy_instances]
        resp = DRSApi.redis_rpc(
            {
                "addresses": proxy_addrs,
                "db_num": 0,
                "password": "",
                "command": "info servers",
                "bk_cloud_id": trans_data.bk_cloud_id,
            }
        )
        proxys_backend_md5 = []
        for ele in resp:
            backends_ret = decode_predixy_info_servers(ele["result"])
            sorted_backends = sorted(backends_ret, key=lambda x: x.server)
            sorted_str = ""
            for bck in sorted_backends:
                sorted_str += bck.__str__() + "\n"
            # 求sorted_str的md5值
            md5 = hashlib.md5(sorted_str.encode("utf-8")).hexdigest()
            proxys_backend_md5.append(
                {
                    "proxy_addr": ele["address"],
                    "backend_md5": md5,
                }
            )
        # 检查md5是否一致
        sorted_md5 = sorted(proxys_backend_md5, key=lambda x: x["backend_md5"])
        if sorted_md5[0]["backend_md5"] != sorted_md5[-1]["backend_md5"]:
            self.log_error(
                "predixy[{}->{}] backends is not same".format(
                    sorted_md5[0]["proxy_addr"], sorted_md5[-1]["proxy_addr"]
                )
            )
            raise Exception(
                "predixy[{}->{}] backends is not same".format(
                    sorted_md5[0]["proxy_addr"], sorted_md5[-1]["proxy_addr"]
                )
            )
