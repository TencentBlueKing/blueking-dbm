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
import logging
import re
import traceback
from typing import List, Tuple

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service, StaticIntervalGenerator

import backend.flow.utils.redis.redis_context_dataclass as flow_context
from backend.components import DRSApi
from backend.db_meta.enums import ClusterType, InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_services.redis.redis_dts.constants import DtsOperateType, DtsTaskType
from backend.db_services.redis.redis_dts.enums import (
    DtsBillType,
    DtsCopyType,
    DtsDataCheckFreq,
    DtsDataCheckType,
    DtsDataRepairMode,
    DtsSyncDisconnReminderFreq,
    DtsSyncDisconnType,
    DtsWriteMode,
    ExecuteMode,
    TimeoutVars,
)
from backend.db_services.redis.redis_dts.models import TbTendisDTSJob, TbTendisDtsTask
from backend.db_services.redis.redis_dts.util import get_safe_regex_pattern
from backend.db_services.redis.util import is_predixy_proxy_type, is_redis_cluster_protocal
from backend.flow.consts import GB, MB, StateType
from backend.flow.engine.bamboo.scene.redis.redis_cluster_apply_flow import RedisClusterApplyFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_data_check_repair import RedisClusterDataCheckRepairFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_open_close import RedisClusterOpenCloseFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_shutdown import RedisClusterShutdownFlow
from backend.flow.engine.bamboo.scene.redis.redis_flush_data import RedisFlushDataFlow
from backend.flow.engine.bamboo.scene.redis.tendis_plus_apply_flow import TendisPlusApplyFlow
from backend.flow.models import FlowTree
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.redis.redis_cluster_nodes import (
    ClusterNodeData,
    decode_cluster_info,
    get_masters_with_slots,
    group_slaves_by_master_id,
)
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, RedisDtsContext
from backend.flow.utils.redis.redis_proxy_util import get_twemproxy_cluster_hash_tag
from backend.ticket.constants import TicketType
from backend.utils.basic import generate_root_id

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
            if not self.check_dst_cluster_connected(
                global_data["bk_biz_id"], kwargs["cluster"]["dts_copy_type"], kwargs["cluster"]["dst"]
            ):
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
        self.log_info("check_all_src_slaves_running slaves_addr:{}".format(slaves_addr))
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
        self.log_info("check_src_redis_host_disk  disk_used:{}".format(disk_used))
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
        self.log_info(
            "check src_cluster:{} cluster_nodes is ok,master_addr:{}".format(src_data["cluster_addr"], master_addr)
        )
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
        self.log_info(
            "check src_cluster:{} cluster_state is ok,master_addr:{}".format(src_data["cluster_addr"], master_addr)
        )
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

    def check_dst_cluster_connected(self, bk_biz_id: int, dts_copy_type: str, dst_data: dict) -> bool:
        """
        检查目的集群是否可连接
        """
        dst_proxy_addrs = []
        dst_domain = ""
        if dts_copy_type == DtsCopyType.COPY_TO_OTHER_SYSTEM:
            dst_proxy_addrs.append(dst_data["cluster_addr"])
        else:
            cluster: Cluster = None
            if (
                dts_copy_type
                in [DtsBillType.REDIS_CLUSTER_SHARD_NUM_UPDATE.value, DtsBillType.REDIS_CLUSTER_TYPE_UPDATE.value]
                and int(dst_data["cluster_id"]) == 0
            ):
                """
                如果是集群分片数变更/集群类型变更,目的集群id为0,代表目的集群是新创建的集群
                """
                dst_addr_pair = dst_data["cluster_addr"].split(":")
                dst_domain = dst_addr_pair[0]
                cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=dst_domain)
            else:
                cluster = Cluster.objects.get(id=dst_data["cluster_id"])
            for proxy in cluster.proxyinstance_set.all():
                dst_proxy_addrs.append(proxy.machine.ip + ":" + str(proxy.port))
        self.log_info("check dst_cluster:{} proxy:{} connect".format(dst_domain, dst_proxy_addrs))
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
        try:
            job_id: int = 0
            task_ids: list = []
            uid = int(global_data["uid"])
            bk_biz_id = int(global_data["bk_biz_id"])
            dts_copy_type = kwargs["cluster"]["dts_copy_type"]
            dst_cluster_id = int(kwargs["cluster"]["dst"]["cluster_id"])
            if (
                dts_copy_type
                in [DtsBillType.REDIS_CLUSTER_SHARD_NUM_UPDATE.value, DtsBillType.REDIS_CLUSTER_TYPE_UPDATE.value]
                and int(kwargs["cluster"]["dst"]["cluster_id"]) == 0
            ):
                """
                如果是集群分片数变更/集群类型变更,目的集群id为0,代表目的集群是新创建的集群
                """
                dst_addr_pair = kwargs["cluster"]["dst"]["cluster_addr"].split(":")
                dst_domain = dst_addr_pair[0]
                cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=dst_domain)
                dst_cluster_id = cluster.id
            src_twemproxy_hash_tag_enabled = 0
            if dts_copy_type != DtsCopyType.USER_BUILT_TO_DBM:
                # 如果不是用户自建集群,则获取twemproxy的hash_tag_enabled
                hash_tag_val = get_twemproxy_cluster_hash_tag(
                    cluster_type=kwargs["cluster"]["src"]["cluster_type"],
                    cluster_id=kwargs["cluster"]["src"]["cluster_id"],
                )
                if hash_tag_val == "{}":
                    src_twemproxy_hash_tag_enabled = 1
            with transaction.atomic():
                job = TbTendisDTSJob()
                job.bill_id = uid
                job.app = str(global_data["bk_biz_id"])
                job.bk_cloud_id = kwargs["cluster"]["src"]["bk_cloud_id"]
                job.user = global_data["created_by"]
                job.dts_bill_type = kwargs["cluster"]["dts_bill_type"]
                job.dts_copy_type = kwargs["cluster"]["dts_copy_type"]
                job.write_mode = global_data.get("write_mode", DtsWriteMode.FLUSHALL_AND_WRITE_TO_REDIS.value)
                job.online_switch_type = (
                    global_data["online_switch_type"] if global_data.get("online_switch_type") else ""
                )

                job.sync_disconnect_type = global_data["sync_disconnect_setting"]["type"]
                job.sync_disconnect_reminder_frequency = global_data["sync_disconnect_setting"].get(
                    "reminder_frequency", DtsSyncDisconnReminderFreq.ONCE_DAILY.value
                )

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
                job.dst_cluster_id = dst_cluster_id
                job.dst_cluster_type = kwargs["cluster"]["dst"]["cluster_type"]
                job.key_white_regex = kwargs["cluster"]["info"]["key_white_regex"]
                job.key_black_regex = kwargs["cluster"]["info"]["key_black_regex"]
                job.create_time = datetime.datetime.now(timezone.utc)
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
                        task.src_twemproxy_hash_tag_enabled = src_twemproxy_hash_tag_enabled
                        task.key_white_regex = task_white_regex
                        task.key_black_regex = task_black_regex
                        task.dst_cluster = kwargs["cluster"]["dst"]["cluster_addr"]
                        task.dst_password = dst_passsword_base64
                        task.create_time = datetime.datetime.now(timezone.utc)
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
            if job_row.last_data_check_repair_flow_id != "":
                stat = FlowTree.objects.get(root_id=job_row.last_data_check_repair_flow_id).status
                if stat == StateType.RUNNING.value:
                    self.log_info(
                        _(
                            "bill_id:{} src_cluster:{} dst_cluster:{} 上次校验修复正在进行中...,flow_id:{}".format(
                                tasks_rows[0].bill_id,
                                tasks_rows[0].src_cluster,
                                tasks_rows[0].dst_cluster,
                                job_row.last_data_check_repair_flow_id,
                            )
                        )
                    )
                    return True
                if stat == StateType.FAILED.value:
                    self.log_error(
                        _(
                            "bill_id:{} src_cluster:{} dst_cluster:{} 上次校验修复失败,flow_id:{},请处理该失败信息而后再到当前页面重试".format(
                                tasks_rows[0].bill_id,
                                tasks_rows[0].src_cluster,
                                tasks_rows[0].dst_cluster,
                                job_row.last_data_check_repair_flow_id,
                            )
                        )
                    )
                    return False
                if stat == StateType.FINISHED.value:
                    self.log_info(
                        _(
                            "bill_id:{} src_cluster:{} dst_cluster:{} 上次校验修复已完成,flow_id:{}".format(
                                tasks_rows[0].bill_id,
                                tasks_rows[0].src_cluster,
                                tasks_rows[0].dst_cluster,
                                job_row.last_data_check_repair_flow_id,
                            )
                        )
                    )
            # 回档实例数据回写 直接断开同步关系
            if global_data["dts_copy_type"] == DtsCopyType.COPY_FROM_ROLLBACK_INSTANCE.value:
                self.log_info(
                    _(
                        "bill_id:{} src_cluster:{} dst_cluster:{} 数据同步已 ok,后续将断开同步关系...".format(
                            job_row.bill_id, job_row.src_cluster, job_row.dst_cluster
                        )
                    )
                )
                self.finish_schedule()
                return True
            # 如果是 集群分片数变更/集群类型变更,且数据校验与修复已经完成,则不断开同步关系,直接返回
            if global_data["ticket_type"] in [
                DtsBillType.REDIS_CLUSTER_SHARD_NUM_UPDATE.value,
                DtsBillType.REDIS_CLUSTER_TYPE_UPDATE.value,
            ]:
                self.log_info(
                    _(
                        "bill_id:{} src_cluster:{} dst_cluster:{} 数据同步已 ok,校验修复已完成,将继续执行等待切换步骤...".format(
                            tasks_rows[0].bill_id, tasks_rows[0].src_cluster, tasks_rows[0].dst_cluster
                        )
                    )
                )
                self.finish_schedule()
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
        current_time = datetime.datetime.now(timezone.utc)
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
        # 指定不做数据校验修复
        if global_data["data_check_repair_setting"]["type"] == DtsDataCheckType.NO_CHECK_NO_REPAIR:
            return False

        # 数据复制后自动断开同步,至少进行一次数据校验
        if global_data["sync_disconnect_setting"]["type"] == DtsSyncDisconnType.AUTO_DISCONNECT_AFTER_REPLICATION:
            if dts_job.last_data_check_repair_flow_id == "":
                return True

        # 集群分片数变更、集群类型变更,至少进行一次数据校验
        if global_data["ticket_type"] in [
            DtsBillType.REDIS_CLUSTER_SHARD_NUM_UPDATE.value,
            DtsBillType.REDIS_CLUSTER_TYPE_UPDATE.value,
        ]:
            if dts_job.last_data_check_repair_flow_id == "":
                return True

        # 到这里时
        # ["data_check_repair_setting"]["type"] 必然是 [DATA_CHECK_AND_REPAIR, DATA_CHECK_ONLY]
        # ["sync_disconnect_setting"]["type"] 必然是 [KEEP_SYNC_WITH_REMINDER]
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
            if task.status != 2 and task.sync_operate not in [
                DtsOperateType.SYNC_STOP_TODO.value,
                DtsOperateType.SYNC_STOP_SUCC.value,
            ]:
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
        root_id = generate_root_id()
        flow = RedisClusterDataCheckRepairFlow(root_id=root_id, data=ticket_data)
        flow.redis_cluster_data_check_repair_flow()
        self.log_info(f"new_data_check_repair_job flow_id:{root_id}")


class RedisDtsExecuteComponent(Component):
    name = __name__
    code = "redis_dts_execute"
    bound_service = RedisDtsExecuteService


class NewDstClusterInstallJobAndWatchStatus(BaseService):
    """
    新建 目标集群安装任务 并检测任务状态
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

        if trans_data.dst_cluster_install_flow_id and trans_data.dst_cluster_install_flow_id != "":
            self.log_info(
                "NewDstClusterInstallJobAndWatchStatus dst_cluster_install_flow_id:{}".format(
                    trans_data.dst_cluster_install_flow_id
                )
            )
            data.outputs["trans_data"] = trans_data
            return True

        ticket_data: dict = {
            "uid": global_data["uid"],
            "ticket_type": TicketType.REDIS_CLUSTER_APPLY.value,
            "bk_biz_id": kwargs["cluster"]["dst_install_param"]["bk_biz_id"],
            "bk_cloud_id": kwargs["cluster"]["dst_install_param"]["bk_cloud_id"],
            "created_by": kwargs["cluster"]["dst_install_param"]["created_by"],
            "proxy_port": kwargs["cluster"]["dst_install_param"]["cluster_port"],
            "domain_name": kwargs["cluster"]["dst_install_param"]["cluster_domain"],
            "cluster_name": kwargs["cluster"]["dst_install_param"]["cluster_name"],
            "cluster_alias": kwargs["cluster"]["dst_install_param"]["cluster_alias"],
            "cluster_type": kwargs["cluster"]["dst_install_param"]["cluster_type"],
            "city_code": kwargs["cluster"]["dst_install_param"].get("region", ""),
            "shard_num": kwargs["cluster"]["dst_install_param"]["shard_num"],
            "group_num": len(kwargs["cluster"]["dst_install_param"]["backend_group"]),
            "maxmemory": kwargs["cluster"]["dst_install_param"]["maxmemory"],
            "db_version": kwargs["cluster"]["dst_install_param"]["db_version"],
            "databases": kwargs["cluster"]["dst_install_param"]["redis_databases"],
            "proxy_pwd": kwargs["cluster"]["dst_install_param"]["cluster_password"],
            "redis_pwd": kwargs["cluster"]["dst_install_param"]["redis_password"],
            "nodes": {
                "proxy": kwargs["cluster"]["dst_install_param"]["proxy"],
                "backend_group": kwargs["cluster"]["dst_install_param"]["backend_group"],
            },
            "resource_spec": kwargs["cluster"]["dst_install_param"]["resource_spec"],
            "disaster_tolerance_level": kwargs["cluster"]["dst_install_param"]["disaster_tolerance_level"],
        }
        if is_predixy_proxy_type(ticket_data["cluster_type"]):
            # 如果是predixy类型,则需要设置proxy_admin_pwd
            # 优先获取用户输入的proxy_admin_pwd,如果没有输入,则使用proxy_pwd
            ticket_data["proxy_admin_pwd"] = kwargs["cluster"]["dst_install_param"].get("redis_proxy_admin_password")
            if not ticket_data.get("proxy_admin_pwd"):
                ticket_data["proxy_admin_pwd"] = ticket_data["proxy_pwd"]
        self.log_info("NewDstClusterInstallJobAndWatchStatus ticket_data==>:{}".format(ticket_data))
        root_id = generate_root_id()
        if ticket_data["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster.value:
            flow = TendisPlusApplyFlow(root_id=root_id, data=ticket_data)
            flow.deploy_tendisplus_cluster_flow()
        elif ticket_data["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance.value:
            flow = RedisClusterApplyFlow(root_id=root_id, data=ticket_data)
            flow.deploy_redis_cluster_flow()
        elif ticket_data["cluster_type"] == ClusterType.TwemproxyTendisSSDInstance.value:
            flow = RedisClusterApplyFlow(root_id=root_id, data=ticket_data)
            flow.deploy_redis_cluster_flow()
        else:
            raise Exception("cluster_type:{} is not support".format(ticket_data["cluster_type"]))

        self.log_info("NewDstClusterInstallJobAndWatchStatus flow_id==>:{}".format(root_id))
        trans_data.dst_cluster_install_flow_id = root_id

        data.outputs["trans_data"] = trans_data
        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data: RedisDtsContext = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        stat = FlowTree.objects.get(root_id=trans_data.dst_cluster_install_flow_id).status
        if stat not in [StateType.FINISHED.value, StateType.FAILED.value]:
            self.log_info(
                "dst_cluster_install_job flow_id:{} status:{}".format(trans_data.dst_cluster_install_flow_id, stat)
            )
            return True
        if stat == StateType.FAILED.value:
            self.log_error("dst_cluster_install_job flow_id:{} failed".format(trans_data.dst_cluster_install_flow_id))
            self.finish_schedule()
            return False

        self.finish_schedule()
        self.log_info("dst_cluster_install_job flow_id:{} finished".format(trans_data.dst_cluster_install_flow_id))
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", requiredc=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class NewDstClusterInstallJobAndWatchStatusComponent(Component):
    name = __name__
    code = "new_dst_cluster_install_job_and_watch_status"
    bound_service = NewDstClusterInstallJobAndWatchStatus


class NewDstClusterFlushJobAndWatchStatus(BaseService):
    """
    新建 目标集群清档任务 并检测任务状态
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

        if trans_data.dst_cluster_flush_flow_id and trans_data.dst_cluster_flush_flow_id != "":
            self.log_info(
                "NewDstClusterFlushJobAndWatchStatus dst_cluster_flush_flow_id:{}".format(
                    trans_data.dst_cluster_flush_flow_id
                )
            )
            data.outputs["trans_data"] = trans_data
            return True
        dst_domain = kwargs["cluster"]["dst"]["cluster_addr"].split(":")[0]
        ticket_data: dict = {
            "uid": global_data["uid"],
            "ticket_type": TicketType.REDIS_PURGE.value,
            "bk_biz_id": global_data["bk_biz_id"],
            "bk_cloud_id": kwargs["cluster"]["dst"]["bk_cloud_id"],
            "created_by": global_data["created_by"],
            "rules": [
                {
                    "cluster_id": kwargs["cluster"]["dst"]["cluster_id"],
                    "cluster_type": kwargs["cluster"]["dst"]["cluster_type"],
                    "domain": dst_domain,
                    "target": "master",
                    "force": True,
                    "backup": True,
                    "db_list": [0],
                    "flushall": True,
                }
            ],
        }
        self.log_info("NewDstClusterFlushJobAndWatchStatus ticket_data==>:{}".format(ticket_data))
        root_id = generate_root_id()
        flow = RedisFlushDataFlow(root_id=root_id, data=ticket_data)
        flow.redis_flush_data_flow()

        self.log_info("NewDstClusterFlushJobAndWatchStatus flow_id==>:{}".format(root_id))
        trans_data.dst_cluster_flush_flow_id = root_id

        data.outputs["trans_data"] = trans_data
        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data: RedisDtsContext = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        stat = FlowTree.objects.get(root_id=trans_data.dst_cluster_flush_flow_id).status
        if stat not in [StateType.FINISHED.value, StateType.FAILED.value]:
            self.log_info(
                "dst_cluster_flush_job flow_id:{} status:{}".format(trans_data.dst_cluster_flush_flow_id, stat)
            )
            return True
        if stat == StateType.FAILED.value:
            self.log_error("dst_cluster_flush_job flow_id:{} failed".format(trans_data.dst_cluster_flush_flow_id))
            self.finish_schedule()
            return False

        self.finish_schedule()
        self.log_info("dst_cluster_flush_job flow_id:{} finished".format(trans_data.dst_cluster_flush_flow_id))
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", requiredc=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class NewDstClusterFlushJobAndWatchStatusComponent(Component):
    name = __name__
    code = "new_dst_cluster_flush_job_and_watch_status"
    bound_service = NewDstClusterFlushJobAndWatchStatus


class NewDtsOnlineSwitchJobAndWatchStatus(BaseService):
    """
    新建 redis dts在线切换任务并且检测任务状态
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

        self.log_info(
            "NewDtsOnlineSwitchJobAndWatchStatus uid=>{} src_cluster_addr:{} dst_cluster_addr:{}".format(
                global_data["uid"], kwargs["cluster"]["src"]["cluster_addr"], kwargs["cluster"]["dst"]["cluster_addr"]
            )
        )
        job_row = TbTendisDTSJob.objects.get(
            bill_id=global_data["uid"],
            src_cluster=kwargs["cluster"]["src"]["cluster_addr"],
            dst_cluster=kwargs["cluster"]["dst"]["cluster_addr"],
        )
        if job_row.online_switch_flow_id != "":
            data.outputs["trans_data"] = trans_data
            return True
        ticket_data: dict = {
            "uid": global_data["uid"],
            "bk_biz_id": global_data["bk_biz_id"],
            "created_by": global_data["created_by"],
            "ticket_type": TicketType.REDIS_DTS_ONLINE_SWITCH.value,
            "online_switch_type": job_row.online_switch_type,
            "infos": [
                {
                    "bill_id": job_row.bill_id,
                    "src_cluster": job_row.src_cluster,
                    "dst_cluster": job_row.dst_cluster,
                }
            ],
        }
        self.log_info(f"new_dts_online_switch_job ticket_data:{ticket_data}")
        from backend.flow.engine.bamboo.scene.redis.redis_cluster_data_copy import RedisClusterDataCopyFlow

        root_id = generate_root_id()
        flow = RedisClusterDataCopyFlow(root_id=root_id, data=ticket_data)
        flow.online_switch_flow()

        job_row.online_switch_flow_id = root_id
        job_row.save(update_fields=["online_switch_flow_id"])

        self.log_info("new_dts_online_switch_job flow_id:{}".format(root_id))
        data.outputs["trans_data"] = trans_data
        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data: RedisDtsContext = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        job_row = TbTendisDTSJob.objects.get(
            bill_id=global_data["uid"],
            src_cluster=kwargs["cluster"]["src"]["cluster_addr"],
            dst_cluster=kwargs["cluster"]["dst"]["cluster_addr"],
        )
        stat = FlowTree.objects.get(root_id=job_row.online_switch_flow_id).status
        if stat not in [StateType.FINISHED.value, StateType.FAILED.value]:
            self.log_info("dts_online_switch_job flow_id:{} status:{}".format(job_row.online_switch_flow_id, stat))
            return True
        if stat == StateType.FAILED.value:
            self.log_error("dts_online_switch_job flow_id:{} failed".format(job_row.online_switch_flow_id))
            self.finish_schedule()
            return False

        self.finish_schedule()
        self.log_info("dts_online_switch_job flow_id:{} finished".format(job_row.online_switch_flow_id))
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", requiredc=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class NewDtsOnlineSwitchJobAndWatchStatusComponent(Component):
    name = __name__
    code = "new_dts_online_switch_job_and_watch_status"
    bound_service = NewDtsOnlineSwitchJobAndWatchStatus


class RedisDtsDisconnectSyncService(BaseService):
    """
    redis dts断开同步关系
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(10)

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data: RedisDtsContext = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        self.log_info(
            "RedisDtsDisconnectSyncService bill_id=>{} src_cluster_addr:{} dst_cluster_addr:{}".format(
                kwargs["cluster"]["bill_id"], kwargs["cluster"]["src_cluster"], kwargs["cluster"]["dst_cluster"]
            )
        )
        with transaction.atomic():
            where = (
                Q(bill_id=kwargs["cluster"]["bill_id"])
                & Q(src_cluster=kwargs["cluster"]["src_cluster"])
                & Q(dst_cluster=kwargs["cluster"]["dst_cluster"])
            )
            for task in TbTendisDtsTask.objects.filter(where):
                if task.sync_operate not in [
                    DtsOperateType.SYNC_STOP_TODO.value,
                    DtsOperateType.SYNC_STOP_SUCC.value,
                ]:
                    task.sync_operate = DtsOperateType.SYNC_STOP_TODO.value
                    task.message = task.sync_operate + "..."
                    task.update_time = datetime.datetime.now(timezone.utc)
                    task.save(update_fields=["sync_operate", "message", "update_time"])
                    self.log_info(
                        "bill_id:{} src_ip:{} src_port:{} operate:{}".format(
                            task.bill_id, task.src_ip, task.src_port, task.sync_operate
                        )
                    )

        data.outputs["trans_data"] = trans_data
        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data: RedisDtsContext = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        running_task_cnt = 0
        failed_task_cnt = 0
        where = (
            Q(bill_id=kwargs["cluster"]["bill_id"])
            & Q(src_cluster=kwargs["cluster"]["src_cluster"])
            & Q(dst_cluster=kwargs["cluster"]["dst_cluster"])
        )
        for task in TbTendisDtsTask.objects.filter(where):
            if task.status < 0:
                failed_task_cnt += 1
            elif task.status in [0, 1]:
                running_task_cnt += 1
        if running_task_cnt > 0:
            self.log_info(
                "uid=>{} src_cluster_addr:{} dst_cluster_addr:{} running_task_cnt:{}".format(
                    kwargs["cluster"]["bill_id"],
                    kwargs["cluster"]["src_cluster"],
                    kwargs["cluster"]["dst_cluster"],
                    running_task_cnt,
                )
            )
            return True
        if failed_task_cnt > 0:
            self.log_error(
                "uid=>{} src_cluster_addr:{} dst_cluster_addr:{} failed_task_cnt:{}".format(
                    kwargs["cluster"]["bill_id"],
                    kwargs["cluster"]["src_cluster"],
                    kwargs["cluster"]["dst_cluster"],
                    failed_task_cnt,
                )
            )
            return False

        self.log_info(
            "uid=>{} src_cluster_addr:{} dst_cluster_addr:{} all tasks competed".format(
                kwargs["cluster"]["bill_id"],
                kwargs["cluster"]["src_cluster"],
                kwargs["cluster"]["dst_cluster"],
            )
        )

        self.finish_schedule()
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", requiredc=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class RedisDtsDisconnectSyncComponent(Component):
    name = __name__
    code = "redis_dts_disconnect_sync"
    bound_service = RedisDtsDisconnectSyncService


class NewDstClusterCloseJobAndWatchStatus(BaseService):
    """
    新建 dst cluster禁用任务并且检测任务状态
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

        self.log_info(
            "NewDstClusterCloseJobAndWatchStatus uid=>{} src_cluster_addr:{} dst_cluster_addr:{}".format(
                global_data["uid"], kwargs["cluster"]["src"]["cluster_addr"], kwargs["cluster"]["dst"]["cluster_addr"]
            )
        )
        job_row = TbTendisDTSJob.objects.get(
            bill_id=global_data["uid"],
            src_cluster=kwargs["cluster"]["src"]["cluster_addr"],
            dst_cluster=kwargs["cluster"]["dst"]["cluster_addr"],
        )
        if job_row.dst_cluster_close_flow_id != "":
            data.outputs["trans_data"] = trans_data
            return True
        ticket_data: dict = {
            "uid": global_data["uid"],
            "bk_biz_id": global_data["bk_biz_id"],
            "created_by": global_data["created_by"],
            "ticket_type": TicketType.REDIS_CLOSE.value,
            "cluster_id": job_row.dst_cluster_id,
            "force": False,
        }
        self.log_info(f"redis_cluster_close dst_cluster:{job_row.dst_cluster} ticket_data:{ticket_data}")
        root_id = generate_root_id()
        flow = RedisClusterOpenCloseFlow(root_id=root_id, data=ticket_data)
        flow.redis_cluster_open_close_flow()

        job_row.dst_cluster_close_flow_id = root_id
        job_row.save(update_fields=["dst_cluster_close_flow_id"])

        self.log_info("new_dst_redis_cluster_close_job flow_id:{}".format(root_id))
        data.outputs["trans_data"] = trans_data
        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data: RedisDtsContext = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        job_row = TbTendisDTSJob.objects.get(
            bill_id=global_data["uid"],
            src_cluster=kwargs["cluster"]["src"]["cluster_addr"],
            dst_cluster=kwargs["cluster"]["dst"]["cluster_addr"],
        )
        stat = FlowTree.objects.get(root_id=job_row.dst_cluster_close_flow_id).status
        if stat not in [StateType.FINISHED.value, StateType.FAILED.value]:
            self.log_info(
                "dst_redis_cluster_close_job flow_id:{} status:{}".format(job_row.dst_cluster_close_flow_id, stat)
            )
            return True
        if stat == StateType.FAILED.value:
            self.log_error(
                "dst_redis_cluster_close_job flow_id:{} failed".format(job_row.dst_cluster_shutdown_flow_id)
            )
            self.finish_schedule()
            return False

        self.finish_schedule()
        self.log_info("dst_redis_cluster_close_job flow_id:{} finished".format(job_row.dst_cluster_shutdown_flow_id))
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", requiredc=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class NewDstClusterCloseJobAndWatchStatusComponent(Component):
    name = __name__
    code = "new_dst_cluster_close_job_and_watch_status"
    bound_service = NewDstClusterCloseJobAndWatchStatus


class NewDstClusterShutdownJobAndWatchStatus(BaseService):
    """
    新建 dst cluster下架任务并且检测任务状态
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

        self.log_info(
            "NewDstClusterShutdownJobAndWatchStatus uid=>{} src_cluster_addr:{} dst_cluster_addr:{}".format(
                global_data["uid"], kwargs["cluster"]["src"]["cluster_addr"], kwargs["cluster"]["dst"]["cluster_addr"]
            )
        )
        job_row = TbTendisDTSJob.objects.get(
            bill_id=global_data["uid"],
            src_cluster=kwargs["cluster"]["src"]["cluster_addr"],
            dst_cluster=kwargs["cluster"]["dst"]["cluster_addr"],
        )
        if job_row.dst_cluster_shutdown_flow_id != "":
            data.outputs["trans_data"] = trans_data
            return True
        ticket_data: dict = {
            "uid": global_data["uid"],
            "bk_biz_id": global_data["bk_biz_id"],
            "created_by": global_data["created_by"],
            "ticket_type": TicketType.REDIS_DESTROY.value,
            "cluster_id": job_row.dst_cluster_id,
        }
        self.log_info(f"redis_cluster_shutdown ticket_data:{ticket_data}")
        root_id = generate_root_id()
        flow = RedisClusterShutdownFlow(root_id=root_id, data=ticket_data)
        flow.redis_cluster_shutdown_flow()

        job_row.dst_cluster_shutdown_flow_id = root_id
        job_row.save(update_fields=["dst_cluster_shutdown_flow_id"])

        self.log_info("new_dst_redis_cluster_shutdown_job flow_id:{}".format(root_id))
        data.outputs["trans_data"] = trans_data
        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data: RedisDtsContext = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        job_row = TbTendisDTSJob.objects.get(
            bill_id=global_data["uid"],
            src_cluster=kwargs["cluster"]["src"]["cluster_addr"],
            dst_cluster=kwargs["cluster"]["dst"]["cluster_addr"],
        )
        stat = FlowTree.objects.get(root_id=job_row.dst_cluster_shutdown_flow_id).status
        if stat not in [StateType.FINISHED.value, StateType.FAILED.value]:
            self.log_info(
                "dst_redis_cluster_shutdown_job flow_id:{} status:{}".format(
                    job_row.dst_cluster_shutdown_flow_id, stat
                )
            )
            return True
        if stat == StateType.FAILED.value:
            self.log_error(
                "dst_redis_cluster_shutdown_job flow_id:{} failed".format(job_row.dst_cluster_shutdown_flow_id)
            )
            self.finish_schedule()
            return False

        self.finish_schedule()
        self.log_info(
            "dst_redis_cluster_shutdown_job flow_id:{} finished".format(job_row.dst_cluster_shutdown_flow_id)
        )
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", requiredc=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class NewDstClusterShutdownJobAndWatchStatusComponent(Component):
    name = __name__
    code = "new_dst_cluster_shutdown_job_and_watch_status"
    bound_service = NewDstClusterShutdownJobAndWatchStatus
