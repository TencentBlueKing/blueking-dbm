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
import logging.config
from dataclasses import asdict
from datetime import datetime, timezone

from django.db.models import Q
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_services.redis.redis_dts.enums import DtsCopyType, DtsDataRepairMode, ExecuteMode
from backend.db_services.redis.redis_dts.models import TbTendisDTSJob, TbTendisDtsTask
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.common.sleep_timer_service import SleepTimerComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import IfTimingAfterNowKwargs
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext

logger = logging.getLogger("flow")


class RedisClusterDataCheckRepairFlow(object):
    """
    redis集群数据校验、修复流程
    """

    def __init__(self, root_id, data):
        self.root_id = root_id
        self.data = data

    def redis_cluster_data_check_repair_flow(self):
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        execution_time: dict = self.__get_exection_time()
        sub_pipelines = []
        for info in self.data["infos"]:
            sub_pipeline = SubBuilder(root_id=self.root_id, data={**self.data, **execution_time})

            if self.data["execute_mode"] == ExecuteMode.SCHEDULED_EXECUTION:
                # 定时执行
                sub_pipeline.add_act(
                    act_name=_("定时"),
                    act_component_code=SleepTimerComponent.code,
                    kwargs=asdict(IfTimingAfterNowKwargs(True)),
                )

            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = CommonContext.__name__
            act_kwargs.file_list = trans_files.redis_base()
            act_kwargs.is_update_trans_data = True
            act_kwargs.cluster = self.__get_dts_job_data(info)

            sub_pipeline.add_act(
                act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
            )

            exec_ips = set()
            for ip in act_kwargs.cluster["src_ips"]:
                exec_ips.add(act_kwargs.cluster["actuator_exec_ip"][ip])
            log_ips_short = ""
            if len(exec_ips) > 1:
                log_ips_short = "{}...{}".format(list(exec_ips)[0], list(exec_ips)[-1])
            else:
                log_ips_short = list(exec_ips)[0]
            act_kwargs.exec_ip = list(exec_ips)
            sub_pipeline.add_act(
                act_name=_("下发介质包,ips:{}").format(log_ips_short),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(act_kwargs),
            )

            acts_list = []
            for ip in act_kwargs.cluster["src_ips"]:
                act_kwargs.cluster["current_src_ip"] = ip
                act_kwargs.exec_ip = act_kwargs.cluster["actuator_exec_ip"][ip]
                act_kwargs.get_redis_payload_func = RedisActPayload.redis_dts_datacheck_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("redis dts数据校验: {}").format(ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list)

            if self.data["data_repair_enabled"]:
                if self.data["repair_mode"] == DtsDataRepairMode.MANUAL_CONFIRM:
                    # 人工确认
                    sub_pipeline.add_act(act_name=_("数据修复人工确认"), act_component_code=PauseComponent.code, kwargs={})

                acts_list = []
                for ip in act_kwargs.cluster["src_ips"]:
                    act_kwargs.cluster["current_src_ip"] = ip
                    act_kwargs.exec_ip = act_kwargs.cluster["actuator_exec_ip"][ip]
                    act_kwargs.get_redis_payload_func = RedisActPayload.redis_dts_datarepair_payload.__name__
                    acts_list.append(
                        {
                            "act_name": _("redis dts数据修复: {}").format(ip),
                            "act_component_code": ExecuteDBActuatorScriptComponent.code,
                            "kwargs": asdict(act_kwargs),
                        }
                    )
                sub_pipeline.add_parallel_acts(acts_list)

            sub_pipelines.append(
                sub_pipeline.build_sub_process(
                    sub_name=_("数据校验与修复,源集群:{} 目的集群:{}").format(info["src_cluster"], info["dst_cluster"]),
                )
            )
        redis_pipeline.add_parallel_sub_pipeline(sub_pipelines)
        return redis_pipeline.run_pipeline()

    def __get_exection_time(self) -> dict:
        if self.data["execute_mode"] == ExecuteMode.AUTO_EXECUTION:
            return {}
        elif self.data["execute_mode"] == ExecuteMode.SCHEDULED_EXECUTION:
            return {"timing": self.data["specified_execution_time"]}

    def __get_dst_proxy_ip(self, info: dict) -> list:
        where = Q(bill_id=info["bill_id"]) & Q(src_cluster=info["src_cluster"]) & Q(dst_cluster=info["dst_cluster"])
        job_row = TbTendisDTSJob.objects.filter(where).first()
        dst_cluster = Cluster.objects.get(id=job_row.dst_cluster_id)
        for proxy in dst_cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
            return [proxy.machine.ip]

    def __get_dts_job_data(self, info: dict) -> dict:
        ret: dict = {}
        first_task: TbTendisDtsTask = None
        where = Q(bill_id=info["bill_id"]) & Q(src_cluster=info["src_cluster"]) & Q(dst_cluster=info["dst_cluster"])
        job_row = TbTendisDTSJob.objects.filter(where).first()
        if not job_row:
            logger.error(
                "get dts job not found,bill_id:{} src_cluster:{} dst_cluster:{}".format(
                    info["bill_id"],
                    info["src_cluster"],
                    info["dst_cluster"],
                )
            )
            raise Exception(
                "get dts job not found,bill_id:{} src_cluster:{} dst_cluster:{}".format(
                    info["bill_id"],
                    info["src_cluster"],
                    info["dst_cluster"],
                )
            )

        # update job last data_check_and_repair info
        job_row.last_data_check_repair_flow_id = self.root_id
        job_row.last_data_check_repair_flow_execute_time = datetime.now(timezone.utc).astimezone()
        job_row.save(update_fields=["last_data_check_repair_flow_id", "last_data_check_repair_flow_execute_time"])

        ret["dts_copy_type"] = job_row.dts_copy_type
        src_ips_set = set()
        if len(info["src_instances"]) == 1 and info["src_instances"][0].upper() == "ALL":
            for row in TbTendisDtsTask.objects.filter(where).all():
                if first_task is None:
                    first_task = row
                src_ips_set.add(row.src_ip)
                if row.src_ip in ret:
                    ret[row.src_ip].append(
                        {"port": row.src_port, "segment_start": row.src_seg_start, "segment_end": row.src_seg_end}
                    )
                else:
                    ret[row.src_ip] = [
                        {"port": row.src_port, "segment_start": row.src_seg_start, "segment_end": row.src_seg_end}
                    ]
        else:
            for src_inst in info["src_instances"]:
                src_ip, src_port = src_inst.split(":")
                for row in TbTendisDtsTask.objects.filter(where).filter(src_ip=src_ip, src_port=int(src_port)).all():
                    if first_task is None:
                        first_task = row
                    src_ips_set.add(row.src_ip)
                    if row.src_ip in ret:
                        ret[row.src_ip].append(
                            {"port": row.src_port, "segment_start": row.src_seg_start, "segment_end": row.src_seg_end}
                        )
                    else:
                        ret[row.src_ip] = [
                            {"port": row.src_port, "segment_start": row.src_seg_start, "segment_end": row.src_seg_end}
                        ]
        if first_task is None:
            logger.error(
                "get dts task not found,bill_id:{} src_cluster:{} dst_cluster:{} src_instances:{}".format(
                    info["bill_id"], info["src_cluster"], info["dst_cluster"], info["src_instances"]
                )
            )
            raise Exception(
                "get dts task not found,bill_id:{} src_cluster:{} dst_cluster:{}".format(
                    info["bill_id"], info["src_cluster"], info["dst_cluster"]
                )
            )
        # 如果是用户自建集群到dbm集群的迁移,则actuator执行机器为目的集群proxy ip
        ret["actuator_exec_ip"] = {}
        src_ips = list(src_ips_set)
        if ret["dts_copy_type"] == DtsCopyType.USER_BUILT_TO_DBM.value:
            proxy_ips = self.__get_dst_proxy_ip(info)
            for ip in src_ips:
                ret["actuator_exec_ip"][ip] = proxy_ips[0]
        else:
            for ip in src_ips:
                ret["actuator_exec_ip"][ip] = ip
        ret["src_hash_tag"] = True if first_task.src_twemproxy_hash_tag_enabled > 0 else False
        ret["src_redis_password"] = base64.b64decode(first_task.src_password).decode("utf-8")
        ret["src_cluster_addr"] = first_task.src_cluster
        ret["dst_cluster_addr"] = first_task.dst_cluster
        ret["dst_cluster_password"] = base64.b64decode(first_task.dst_password).decode("utf-8")
        ret["key_white_regex"] = info["key_white_regex"]
        ret["key_black_regex"] = info["key_black_regex"]
        ret["src_ips"] = src_ips
        return ret
