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
import uuid
from typing import List, Tuple

from django.db import transaction
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service, StaticIntervalGenerator

import backend.flow.utils.redis.redis_context_dataclass as flow_context
from backend.components import DRSApi
from backend.db_meta.enums import ClusterType, InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_services.redis.redis_dts.constants import DtsOperateType, DtsTaskType
from backend.db_services.redis.redis_dts.enums import (
    DtsCopyType,
    DtsDataCheckFreq,
    DtsDataCheckType,
    DtsDataRepairMode,
    DtsSyncDisconnType,
    ExecuteMode,
    TimeoutVars,
)
from backend.db_services.redis.redis_dts.models import TbTendisDTSJob, TbTendisDtsTask
from backend.db_services.redis.redis_dts.util import (
    get_safe_regex_pattern,
    is_predixy_proxy_type,
    is_redis_cluster_protocal,
    is_twemproxy_proxy_type,
)
from backend.flow.consts import GB, MB, StateType
from backend.flow.engine.bamboo.scene.redis.redis_cluster_data_check_repair import RedisClusterDataCheckRepairFlow
from backend.flow.models import FlowTree
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.redis.redis_cluster_nodes import (
    ClusterNodeData,
    decode_cluster_info,
    get_masters_with_slots,
    group_slaves_by_master_id,
)
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, RedisDtsContext
from backend.flow.utils.redis.redis_proxy_util import decode_predixy_info_servers, decode_twemproxy_backends
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class RedisDtsPrecheckService(BaseService):
    """
    redis dts前置检查
    """

    def _execute(self, data, parent_data):
        kwargs: ActKwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data: RedisDtsContext = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        # 打印信息
        self.log_info(" RedisDtsPrecheckService start")
        self.log_info("kwargs: {}".format(kwargs))
        try:
            # 检查key正则是否合法
            if not self.check_key_regex(kwargs):
                return False
            # 所有slave必须是running状态且可连接
            if not self.check_all_src_slaves_running(kwargs["cluster"]["src"]):
                return False
            # 源slave磁盘空间是否足够
            if not self.check_src_redis_host_disk(trans_data, kwargs):
                return False
            # 源集群如果是cluster协议,则检查集群状态是否ok
            if not self.check_src_cluster_state_ok(kwargs["cluster"]["src"]):
                return False
            # 源集群如果是cluster协议,则检查集群节点是否正常
            self.log_info("start check_src_cluster_nodes_ok")
            self.check_src_cluster_nodes_ok(kwargs["cluster"]["dts_copy_type"], kwargs["cluster"]["src"])
            # cluster_nice_slaves = self.check_src_cluster_nodes_ok(trans_data)
            # if not cluster_nice_slaves and len(cluster_nice_slaves) > 0:
            #     trans_data.src_slave_instances = cluster_nice_slaves

            # 目的集群可连接性
            if not self.check_dst_cluster_connected(kwargs["cluster"]["dts_copy_type"], kwargs["cluster"]["dst"]):
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

    def check_key_regex(self, kwargs: dict) -> bool:
        """
        检查key的正则表达式是否合法
        """
        white_regex = get_safe_regex_pattern(kwargs["cluster"]["info"]["key_white_regex"])
        black_regex = get_safe_regex_pattern(kwargs["cluster"]["info"]["key_black_regex"])

        if white_regex == "":
            self.log_error(_("包含key正则:{} 不合法".format(kwargs["cluster"]["info"]["key_white_regex"])))
            return False

        if black_regex == ".*":
            self.log_error(_("排除key正则:{} 不合法".format(kwargs["cluster"]["info"]["key_black_regex"])))
            return False

        if white_regex != ".*" and white_regex != "":
            try:
                re.compile(white_regex)
            except Exception as e:
                self.log_error(_("包含key正则:{} 不合法,err:{}".format(kwargs["cluster"]["info"]["key_white_regex"], e)))
                return False

        if black_regex != "":
            try:
                re.compile(black_regex)
            except Exception as e:
                self.log_error(_("排除key正则:{} 不合法,err:{}".format(kwargs["cluster"]["info"]["key_black_regex"], e)))
                return False
        return True

    def check_all_src_slaves_running(self, src_data: dict) -> bool:
        """
        检查所有源redis slave是否都是running状态
        """
        unrunning_slave_cnt = 0
        for slave in src_data["slave_instances"]:
            if slave["status"] != InstanceStatus.RUNNING.value:
                unrunning_slave_cnt += 1
        if unrunning_slave_cnt > 0:
            self.log_error(_("源redis集群{}存在{}个非running状态的slave".format(src_data["cluster_addr"], unrunning_slave_cnt)))
            return False
        slaves_addr = [slave["ip"] + ":" + str(slave["port"]) for slave in src_data["slave_instances"]]
        DRSApi.redis_rpc(
            {
                "addresses": slaves_addr,
                "db_num": 0,
                "password": src_data["redis_password"],
                "command": "ping",
                "bk_cloud_id": src_data["bk_cloud_id"],
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

    def check_src_redis_host_disk(self, trans_data: RedisDtsContext, kwargs: dict) -> bool:
        """
        检查源redis磁盘空间是否足够
        """
        if kwargs["cluster"]["dts_copy_type"] == DtsCopyType.USER_BUILT_TO_DBM.value:
            return True
        disk_used = trans_data.disk_used
        for src_slave in kwargs["cluster"]["src"]["slave_instances"]:
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
        slave_hosts = set(host["ip"] for host in kwargs["cluster"]["src"]["slave_instances"])
        self.log_info(_("所有源redis slave机器:{} 磁盘空间检查通过").format(slave_hosts))
        return True

    def check_src_cluster_nodes_ok(self, dts_copy_type: str, src_data: dict) -> List[dict]:
        """
        如果源集群是redis cluster协议,检查源集群节点是否正常:
        1. 每个负责slot的master都至少有一个running的slave
        2. 如果有多个running slave,则选择其中一个作为迁移节点
        """
        if not is_redis_cluster_protocal(src_data["cluster_type"]):
            self.log_info(
                _("src_cluster:{} type:{} 无需检查cluster nodes是否ok").format(
                    src_data["cluster_addr"], src_data["cluster_type"]
                )
            )
            return []
        if dts_copy_type == DtsCopyType.USER_BUILT_TO_DBM.value:
            # 用户自建集群,cluster nodes无需再次获取
            return []

        # 获取集群cluster nodes信息
        running_master = src_data["one_running_master"]
        master_addr = running_master["ip"] + ":" + str(running_master["port"])
        resp = DRSApi.redis_rpc(
            {
                "addresses": [master_addr],
                "db_num": 0,
                "password": src_data["redis_password"],
                "command": "cluster nodes",
                "bk_cloud_id": src_data["bk_cloud_id"],
            }
        )
        cluster_nodes_str = resp[0]["result"]
        self.log_info("src_cluster:{} cluster_nodes_str:\n {}".format(src_data["cluster_addr"], cluster_nodes_str))
        # 确保所有负责slots的master都至少有一个running的slave
        # 如果有多个running slave,则选择其中一个保存到nice_slaves中
        masters_with_slots = get_masters_with_slots(cluster_nodes_str)
        if len(masters_with_slots) == 0:
            self.log_error(
                "src_cluster:{} not found masters(with_slots),master:{}".format(src_data["cluster_addr"], master_addr)
            )
            raise Exception(
                "src_cluster:{} not found masters(with_slots),master:{}".format(src_data["cluster_addr"], master_addr)
            )
        slaves_by_masterid = group_slaves_by_master_id(cluster_nodes_str)
        meta_slaves = {}
        for src_slave in src_data["slave_instances"]:
            addr = src_slave["ip"] + ":" + str(src_slave["port"])
            meta_slaves[addr] = src_slave
        nice_slaves = []
        for master in masters_with_slots:
            if master.node_id not in slaves_by_masterid:
                self.log_error("src_cluster({}) master {} has no slave".format(src_data["cluster_addr"], master.addr))
                raise Exception("src_cluster({}) master {} has no slave".format(src_data["cluster_addr"], master.addr))
            slaves = slaves_by_masterid[master.node_id]
            one_running_slave: ClusterNodeData = None
            for slave in slaves:
                if slave.is_running() and (slave.addr in meta_slaves):
                    # slave 必须是running状态,并且在db_meta中存在
                    one_running_slave = slave
                    break
            if one_running_slave is None:
                self.log_error(
                    "src_cluster({}) master {} has no running slave".format(src_data["cluster_addr"], master.addr)
                )
                raise Exception(
                    "src_cluster({}) master {} has no running slave".format(src_data["cluster_addr"], master.addr)
                )
            nice_slaves.append(meta_slaves[one_running_slave.addr])
        self.log_info("check_src_cluster_nodes_ok nice_slaves:{}".format(nice_slaves))
        return nice_slaves

    def check_src_cluster_state_ok(self, src_data: dict) -> bool:
        """
        如果源集群是redis cluster协议,检查源集群cluster_state是ok的
        """
        if not is_redis_cluster_protocal(src_data["cluster_type"]):
            self.log_info(
                _("src_cluster:{} 类型是:{} 无需检查cluster state".format(src_data["cluster_addr"], src_data["cluster_type"]))
            )
            return True
        running_master = src_data["one_running_master"]
        master_addr = running_master["ip"] + ":" + str(running_master["port"])
        resp = DRSApi.redis_rpc(
            {
                "addresses": [master_addr],
                "db_num": 0,
                "password": src_data["redis_password"],
                "command": "cluster info",
                "bk_cloud_id": src_data["bk_cloud_id"],
            }
        )
        cluster_info_str = resp[0]["result"]
        cluster_info = decode_cluster_info(cluster_info_str)
        if cluster_info.cluster_state != "ok":
            self.log_error(
                "src cluster:{} cluster_state:{} is not ok".format(
                    src_data["cluster_addr"], cluster_info.cluster_state
                )
            )
            # raise Exception(
            #     "src cluster:{} cluster_state:{} is not ok".format(
            #         trans_data.src_cluster_addr, cluster_info.cluster_state
            #     )
            # )
            return False
        self.log_info("src_cluster:{} cluster_state:{}".format(src_data["cluster_addr"], cluster_info.cluster_state))
        return True

    def check_dst_cluster_connected(self, dts_copy_type: str, dst_data: dict) -> bool:
        """
        检查目的集群是否可连接
        """
        # TODO 现在域名无法使用,目的集群先用 proxy_ip:proxy_port 代替
        dst_proxy_addrs = []
        if dts_copy_type == DtsCopyType.COPY_TO_OTHER_SYSTEM:
            dst_proxy_addrs.append(dst_data["cluster_addr"])
        else:
            cluster = Cluster.objects.get(id=dst_data["cluster_id"])
            for proxy in cluster.proxyinstance_set.all():
                dst_proxy_addrs.append(proxy.machine.ip + ":" + str(proxy.port))
        DRSApi.redis_rpc(
            {
                "addresses": dst_proxy_addrs,
                "db_num": 0,
                "password": dst_data["cluster_password"],
                "command": "get a",
                "bk_cloud_id": dst_data["bk_cloud_id"],
            }
        )
        self.log_info("dst_cluster:{} connect success".format(dst_data["cluster_addr"]))
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
    interval = StaticIntervalGenerator(30)

    def _execute(self, data, parent_data):
        kwargs: ActKwargs = data.get_one_of_inputs("kwargs")
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
                job.app = str(global_data["bk_biz_id"])
                job.bk_cloud_id = kwargs["cluster"]["src"]["bk_cloud_id"]
                job.user = global_data["created_by"]
                job.dts_bill_type = kwargs["cluster"]["dts_bill_type"]
                job.dts_copy_type = kwargs["cluster"]["dts_copy_type"]
                job.write_mode = global_data["write_mode"]
                job.online_switch_type = (
                    global_data["online_switch_type"] if global_data.get("online_switch_type") else ""
                )

                job.sync_disconnect_type = global_data["sync_disconnect_setting"]["type"]
                job.sync_disconnect_reminder_frequency = global_data["sync_disconnect_setting"]["reminder_frequency"]

                job.data_check_repair_type = global_data["data_check_repair_setting"]["type"]
                job.data_check_repair_execution_frequency = global_data["data_check_repair_setting"][
                    "execution_frequency"
                ]

                job.src_cluster = kwargs["cluster"]["src"]["cluster_addr"]
                job.src_cluster_id = kwargs["cluster"]["src"]["cluster_id"]
                job.src_cluster_type = kwargs["cluster"]["src"]["cluster_type"]

                job.src_rollback_bill_id = 0
                job.src_rollback_instances = ""

                job.dst_bk_biz_id = (
                    kwargs["cluster"]["info"].get("dst_bk_biz_id")
                    if kwargs["cluster"]["info"].get("dst_bk_biz_id")
                    else global_data["bk_biz_id"]
                )
                job.dst_cluster = kwargs["cluster"]["dst"]["cluster_addr"]
                job.dst_cluster_id = kwargs["cluster"]["dst"]["cluster_id"]
                job.dst_cluster_type = kwargs["cluster"]["dst"]["cluster_type"]
                job.key_white_regex = kwargs["cluster"]["info"]["key_white_regex"]
                job.key_black_regex = kwargs["cluster"]["info"]["key_black_regex"]
                job.create_time = datetime.datetime.now()
                job.save()
                job_id = job.id

                src_password_base64 = base64.b64encode(
                    kwargs["cluster"]["src"]["redis_password"].encode("utf-8")
                ).decode("utf-8")
                dst_passsword_base64 = base64.b64encode(
                    kwargs["cluster"]["dst"]["cluster_password"].encode("utf-8")
                ).decode("utf-8")
                task_white_regex = get_safe_regex_pattern(kwargs["cluster"]["info"]["key_white_regex"])
                task_black_regex = get_safe_regex_pattern(kwargs["cluster"]["info"]["key_black_regex"])

                cuncurrency_limit = self.get_src_redis_host_concurrency(trans_data, kwargs)
                for slave in kwargs["cluster"]["src"]["slave_instances"]:
                    addr = slave["ip"] + ":" + str(slave["port"])
                    for kvstoreid in range(slave["kvstorecount"]):
                        task = TbTendisDtsTask()
                        task.bill_id = job.bill_id
                        task.user = job.user
                        task.app = job.app
                        task.bk_cloud_id = job.bk_cloud_id
                        task.write_mode = job.write_mode
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
                        task.src_ip_zonename = kwargs["cluster"]["src"]["cluster_city_name"]
                        task.src_kvstore_id = kvstoreid
                        task.key_white_regex = task_white_regex
                        task.key_black_regex = task_black_regex
                        task.dst_cluster = kwargs["cluster"]["dst"]["cluster_addr"]
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
        job_row = TbTendisDTSJob.objects.get(id=trans_data.job_id)
        all_done, all_success = self.__is_all_tasks_done(tasks_rows)
        if all_done:
            # 所有的task都已经完成了
            if all_success:
                # 所有的task都成功了
                self.log_info(
                    _(
                        "bill_id:{} src_cluster:{} dst_cluster:{} 所有tasks都成功且终止了同步task".format(
                            tasks_rows[0].bill_id, tasks_rows[0].src_cluster, tasks_rows[0].dst_cluster
                        )
                    )
                )
                self.finish_schedule()
                return True
            else:
                # 有task失败了
                self.log_error(
                    _(
                        "bill_id:{} src_cluster:{} dst_cluster:{} 某些tasks迁移失败".format(
                            tasks_rows[0].bill_id, tasks_rows[0].src_cluster, tasks_rows[0].dst_cluster
                        )
                    )
                )
                self.finish_schedule()
                return False
        if self.__is_all_tasks_incr_sync(tasks_rows):
            self.log_info(
                _(
                    "bill_id:{} src_cluster:{} dst_cluster:{} 所有tasks都是增量同步".format(
                        tasks_rows[0].bill_id, tasks_rows[0].src_cluster, tasks_rows[0].dst_cluster
                    )
                )
            )
            if self.__is_able_to_new_check_repair(global_data, job_row):
                self.log_info(
                    _(
                        "bill_id:{} src_cluster:{} dst_cluster:{} 开始新的校验修复".format(
                            tasks_rows[0].bill_id, tasks_rows[0].src_cluster, tasks_rows[0].dst_cluster
                        )
                    )
                )
                self.__new_data_check_repair_job(global_data, job_row)
                return True

            if self.__is_able_to_disconnect(global_data, job_row):
                self.log_info(
                    _(
                        "bill_id:{} src_cluster:{} dst_cluster:{} 所有tasks开始断开同步关系".format(
                            tasks_rows[0].bill_id, tasks_rows[0].src_cluster, tasks_rows[0].dst_cluster
                        )
                    )
                )
                self.__disconnect_all_tasks_sync(tasks_rows)
                return True

        # 继续下次循环
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", requiredc=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def get_src_redis_host_concurrency(self, trans_data: RedisDtsContext, kwargs: ActKwargs) -> int:
        """
        获取源redis host上可支持的并发度,对tendisSSD尤为重要,否则容易把磁盘搞满
        """
        max_datasize_instance: dict = None
        for slave in kwargs["cluster"]["src"]["slave_instances"]:
            if max_datasize_instance is None:
                max_datasize_instance = slave
                continue
            if max_datasize_instance["data_size"] < slave["data_size"]:
                max_datasize_instance = slave
        if kwargs["cluster"]["dts_copy_type"] == DtsCopyType.USER_BUILT_TO_DBM:
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

    def __is_all_tasks_done(self, tasks: List[TbTendisDtsTask]) -> Tuple[bool, bool]:
        """
        判断是否所有任务都完成
        """
        all_done: bool = True
        all_success: bool = True
        for task in tasks:
            if task.status in [0, 1]:
                # 存在tasks.status in [0,1]的情况
                all_done = False
                all_success = False
                return all_done, all_success
            if task.status != 2:
                # 存在失败的情况
                all_success = False
        return all_done, all_success

    def __is_check_time_interval_satisfied(self, execution_frequency: str, last_execute_time: datetime) -> bool:
        """
        判断是否满足校验时间间隔
        """
        current_time = datetime.datetime.now()
        if execution_frequency == DtsDataCheckFreq.ONCE_EVERY_THREE_DAYS:
            if (current_time - last_execute_time).days < 3:
                return False
        if execution_frequency == DtsDataCheckFreq.ONCE_WEEKLY:
            if (current_time - last_execute_time).days < 7:
                return False
        return True

    def __is_able_to_new_check_repair(self, global_data: dict, dts_job: TbTendisDTSJob) -> bool:
        """
        判断是否可以进行数据校验修复
        """
        if global_data["data_check_repair_setting"]["type"] == DtsDataCheckType.NO_CHECK_NO_REPAIR:
            return False

        if global_data["sync_disconnect_setting"]["type"] == DtsSyncDisconnType.AUTO_DISCONNECT_AFTER_REPLICATION:
            if dts_job.last_data_check_repair_flow_id == "":
                return True

        if global_data["sync_disconnect_setting"]["type"] == DtsSyncDisconnType.KEEP_SYNC_WITH_REMINDER:
            if dts_job.last_data_check_repair_flow_id == "":
                # 第一次发起校验修复
                return True
            stat = FlowTree.objects.get(root_id=dts_job.last_data_check_repair_flow_id).status
            if stat not in [StateType.FAILED, StateType.FINISHED]:
                # 上次校验修复未完成
                return False
            # 上次校验修复已完成
            if (
                global_data["data_check_repair_setting"]["execution_frequency"]
                == DtsDataCheckFreq.ONCE_AFTER_REPLICATION
            ):
                # 复制完成后执行一次校验修复
                return False
            if self.__is_check_time_interval_satisfied(
                global_data["data_check_repair_setting"]["execution_frequency"],
                dts_job.last_data_check_repair_flow_execute_time,
            ):
                return True
        return False

    def __is_able_to_disconnect(self, global_data: dict, dts_job: TbTendisDTSJob) -> bool:
        """
        判断是否可以断开同步关系
        """
        if global_data["sync_disconnect_setting"]["type"] == DtsSyncDisconnType.AUTO_DISCONNECT_AFTER_REPLICATION:
            # 复制完成后自动断开同步关系,并且需要进行数据校验修复,则需要等待数据校验修复完成后再断开同步关系
            if dts_job.last_data_check_repair_flow_id != "":
                stat = FlowTree.objects.get(root_id=dts_job.last_data_check_repair_flow_id).status
                if stat == StateType.FINISHED:
                    return True
            return False

        # 数据复制完成后保持同步关系
        # global_data["sync_disconnect_setting"]["type"] ==  keep_sync_with_reminder
        return False

    @transaction.atomic()
    def __disconnect_all_tasks_sync(self, tasks: List[TbTendisDtsTask]):
        """
        执行断开同步
        """
        for task in tasks:
            task.sync_operate = DtsOperateType.SYNC_STOP_TODO
            task.save(update_fields=["sync_operate"])

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

    def __new_data_check_repair_job(self, global_data: dict, dts_job: TbTendisDTSJob):
        repair_enabled: bool = (
            global_data["data_check_repair_setting"]["type"] == DtsDataCheckType.DATA_CHECK_AND_REPAIR.value
            or global_data["sync_disconnect_setting"]["type"]
            == DtsSyncDisconnType.AUTO_DISCONNECT_AFTER_REPLICATION.value
        )
        ticket_data: dict = {
            "uid": global_data["uid"],
            "bk_biz_id": global_data["bk_biz_id"],
            "created_by": global_data["created_by"],
            "ticket_type": TicketType.REDIS_DATACOPY_CHECK_REPAIR.value,
            "execute_mode": ExecuteMode.AUTO_EXECUTION.value,
            "specified_execution_time": "",
            "global_timeout": TimeoutVars.NEVER.value,
            "data_repair_enabled": repair_enabled,
            "repair_mode": DtsDataRepairMode.AUTO_REPAIR.value,
            "infos": [
                {
                    "bill_id": dts_job.bill_id,
                    "src_cluster": dts_job.src_cluster,
                    "src_instances": ["all"],
                    "dst_cluster": dts_job.dst_cluster,
                    "key_white_regex": dts_job.key_white_regex,
                    "key_black_regex": dts_job.key_black_regex,
                }
            ],
        }
        self.log_info(f"new_data_check_repair_job ticket_data:{ticket_data}")
        root_id = uuid.uuid1().hex
        flow = RedisClusterDataCheckRepairFlow(root_id=root_id, data=ticket_data)
        flow.redis_cluster_data_check_repair_flow()


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
