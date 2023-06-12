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
import logging.config
from dataclasses import asdict

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_services.redis_dts.constants import DtsCopyType
from backend.flow.consts import WriteContextOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.exec_shell_script import ExecuteShellScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_dts import (
    GetRedisDtsDataComponent,
    GetRedisDtsDataService,
    RedisDtsExecuteComponent,
    RedisDtsPrecheckComponent,
)
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, RedisDtsContext

logger = logging.getLogger("flow")


class RedisClusterDtsFlow(object):
    """
    redis集群dts
    """

    def __init__(self, root_id, data):
        self.root_id = root_id
        self.data = data

    def redis_cluster_dts_flow(self):
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        sub_pipelines = []
        for rule in self.data["rules"]:
            logger.info("redis_cluster_dts_flow rule:{}".format(rule))
            slave_hosts = []
            if self.data["dts_copy_type"] != DtsCopyType.USER_BUILT_TO_DBM.value:
                instances_ret = GetRedisDtsDataService.get_cluster_slaves_data(
                    self.data["bk_biz_id"], rule["src_cluster"]
                )
                slave_hosts = instances_ret[1]
            cluster = {
                **rule,
                "dts_bill_type": self.data["dts_bill_type"],
                "dts_copy_type": self.data["dts_copy_type"],
            }

            src_cluster_info = self.__get_src_cluster_info(self.data["bk_biz_id"], self.data["dts_copy_type"], cluster)
            dst_cluster_info = self.__get_dst_cluster_info(self.data["bk_biz_id"], self.data["dts_copy_type"], cluster)
            cluster["meta_src_cluster_data"] = src_cluster_info
            cluster["meta_dst_cluster_data"] = dst_cluster_info

            exec_ip = list(src_cluster_info["ports_group_by_ip"].keys())
            logger.info("redis_cluster_dts_flow src_slave_ips:{}".format(exec_ip))

            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = RedisDtsContext.__name__
            act_kwargs.file_list = trans_files.redis_base()
            act_kwargs.is_update_trans_data = True
            act_kwargs.cluster = cluster
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            sub_pipeline.add_act(
                act_name=_("获取源集群、目的集群信息"), act_component_code=GetRedisDtsDataComponent.code, kwargs=asdict(act_kwargs)
            )
            if self.data["dts_copy_type"] != DtsCopyType.USER_BUILT_TO_DBM.value:
                acts_list = []
                for host in slave_hosts:
                    # 获取slave磁盘信息
                    act_kwargs.exec_ip = host["ip"]
                    act_kwargs.write_op = WriteContextOpType.APPEND.value
                    act_kwargs.cluster[
                        "shell_command"
                    ] = """
                            d=`df -k $REDIS_BACKUP_DIR | grep -iv Filesystem`
                            echo "<ctx>{\\\"data\\\":\\\"${d}\\\"}</ctx>"
                            """
                    acts_list.append(
                        {
                            "act_name": _("获取磁盘使用情况: {}").format(host["ip"]),
                            "act_component_code": ExecuteShellScriptComponent.code,
                            "kwargs": asdict(act_kwargs),
                            "write_payload_var": "disk_used",
                        }
                    )
                sub_pipeline.add_parallel_acts(acts_list=acts_list)

            sub_pipeline.add_act(
                act_name=_("redis dts前置检查"),
                act_component_code=RedisDtsPrecheckComponent.code,
                kwargs=asdict(act_kwargs),
            )
            sub_pipeline.add_act(
                act_name=_("redis dts发起任务并等待至增量同步阶段"),
                act_component_code=RedisDtsExecuteComponent.code,
                kwargs=asdict(act_kwargs),
            )
            sub_pipeline.add_act(
                act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
            )

            act_kwargs.exec_ip = exec_ip
            sub_pipeline.add_act(
                act_name=_("下发介质包"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
            )

            acts_list = []
            for ip in src_cluster_info["ports_group_by_ip"]:
                act_kwargs.exec_ip = ip
                act_kwargs.get_redis_payload_func = RedisActPayload.redis_dts_datacheck_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("redis dts数据校验: {}").format(ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)
            sub_pipelines.append(
                sub_pipeline.build_sub_process(
                    sub_name=_("源集群:{} 数据迁移到 目的集群:{}").format(cluster["src_cluster"], cluster["dst_cluster"])
                )
            )
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()

    def __get_src_cluster_info(self, bk_biz_id: int, dts_copy_type: str, input_rule: dict) -> dict:
        src_cluster = {}
        ports_group_by_ip = {}
        if dts_copy_type == DtsCopyType.USER_BUILT_TO_DBM:
            src_cluster["src_cluster_addr"] = input_rule.get("src_cluster")
            src_cluster["src_cluster_password"] = input_rule.get("src_cluster_password")
            src_cluster["src_cluster_type"] = input_rule.get("src_cluster_type")
        else:
            src_cluster_data = GetRedisDtsDataService.get_cluster_info_by_domain(bk_biz_id, input_rule["src_cluster"])
            src_cluster["src_cluster_addr"] = (
                src_cluster_data["cluster_domain"] + ":" + str(src_cluster_data["cluster_port"])
            )
            src_cluster["src_cluster_password"] = src_cluster_data["cluster_password"]
            src_cluster["src_cluster_type"] = src_cluster_data["cluster_type"]
            src_cluster["src_redis_password"] = src_cluster_data["redis_password"]

            src_redis_data = GetRedisDtsDataService.get_cluster_slaves_data(
                bk_biz_id, src_cluster_data["cluster_domain"]
            )
            logger.info("src_redis_data:{}".format(src_redis_data))
            for instance in src_redis_data[1]:
                ip = instance["ip"]
                if ip not in ports_group_by_ip:
                    ports_group_by_ip[ip] = []
                ports_group_by_ip[ip].append(
                    {
                        "port": instance["port"],
                        "segment_start": instance["segment_start"],
                        "segment_end": instance["segment_end"],
                    }
                )
            src_cluster["ports_group_by_ip"] = ports_group_by_ip
        return src_cluster

    def __get_dst_cluster_info(self, bk_biz_id: int, dts_copy_type: str, input_rule: dict) -> dict:
        dst_cluster = {}
        if dts_copy_type == DtsCopyType.COPY_TO_OTHER_SYSTEM:
            dst_cluster["dst_cluster_addr"] = input_rule.get("dst_cluster")
            dst_cluster["dst_cluster_password"] = input_rule.get("dst_cluster_password")
        else:
            dst_cluster_data = GetRedisDtsDataService.get_cluster_info_by_domain(bk_biz_id, input_rule["dst_cluster"])
            dst_cluster["dst_cluster_addr"] = (
                dst_cluster_data["cluster_domain"] + ":" + str(dst_cluster_data["cluster_port"])
            )
            dst_cluster["dst_cluster_password"] = dst_cluster_data["cluster_password"]
            dst_cluster["dst_cluster_type"] = dst_cluster_data["cluster_type"]
        return dst_cluster
