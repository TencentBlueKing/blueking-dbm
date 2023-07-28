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
from typing import Dict

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_services.redis_dts.enums import DtsCopyType
from backend.flow.consts import RedisBackupEnum, WriteContextOpType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.exec_shell_script import ExecuteShellScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_dts import (
    RedisDtsExecuteComponent,
    RedisDtsPrecheckComponent,
)
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs
from backend.flow.utils.redis.redis_util import domain_without_port


def redis_dts_data_copy_atom_job(root_id, ticket_data, act_kwargs: ActKwargs) -> SubBuilder:
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    sub_pipeline.add_act(
        act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
    )
    if ticket_data["dts_copy_type"] != DtsCopyType.USER_BUILT_TO_DBM.value:
        acts_list = []
        for host in act_kwargs.cluster["src"]["slave_hosts"]:
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
        act_name=_("redis dts前置检查,{}->{}").format(
            act_kwargs.cluster["src"]["cluster_addr"], act_kwargs.cluster["dst"]["cluster_addr"]
        ),
        act_component_code=RedisDtsPrecheckComponent.code,
        kwargs=asdict(act_kwargs),
    )
    sub_pipeline.add_act(
        act_name=_("redis dts发起任务并等待至增量同步阶段"),
        act_component_code=RedisDtsExecuteComponent.code,
        kwargs=asdict(act_kwargs),
    )
    return sub_pipeline.build_sub_process(sub_name=_("redis dts任务发起并等待同步完成"))


def generate_dst_cluster_backup_flush_info(act_kwargs: ActKwargs) -> dict:
    dst_running_masters = act_kwargs.cluster["dst"]["running_masters"]
    ret = {
        "backup_type": RedisBackupEnum.NORMAL_BACKUP.value,
        "domain_name": domain_without_port(act_kwargs.cluster["dst"]["cluster_addr"]),
        "cluster_type": act_kwargs.cluster["dst"]["cluster_type"],
        "force": True,
        "requirepass": act_kwargs.cluster["dst"]["redis_password"],
        "db_list": [0],
        "flushall": True,
        "db_version": act_kwargs.cluster["dst"]["major_version"],
    }
    for master in dst_running_masters:
        if master["ip"] in ret:
            ret[master["ip"]].append(master["port"])
        else:
            ret[master["ip"]] = [master["port"]]
    return ret


def redis_dst_cluster_backup_and_flush(root_id, ticket_data, act_kwargs: ActKwargs) -> SubBuilder:
    dst_master_ips = set()
    for dst_master in act_kwargs.cluster["dst"]["running_masters"]:
        dst_master_ips.add(dst_master["ip"])

    # 保存原始cluster信息
    cluster_bak = act_kwargs.cluster

    # 替换成 flush 和 backup 的 cluster 信息
    backup_flush_cluster = generate_dst_cluster_backup_flush_info(act_kwargs)
    act_kwargs.cluster = backup_flush_cluster

    trans_files = GetFileList(db_type=DBType.Redis)
    act_kwargs.file_list = trans_files.redis_base()
    act_kwargs.exec_ip = list(dst_master_ips)

    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    sub_pipeline.add_act(
        act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
    )
    sub_pipeline.add_act(act_name=_("下发介质包"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs))

    acts_list = []
    for dst_master_ip in dst_master_ips:
        act_kwargs.exec_ip = dst_master_ip
        act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_backup_payload.__name__
        acts_list.append(
            {
                "act_name": _("redis备份: {}").format(dst_master_ip),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
                "write_payload_var": "tendis_backup_info",
            }
        )
    if acts_list:
        sub_pipeline.add_parallel_acts(acts_list=acts_list)

    acts_list = []
    for dst_master_ip in dst_master_ips:
        act_kwargs.exec_ip = dst_master_ip
        act_kwargs.get_redis_payload_func = RedisActPayload.redis_flush_data_payload.__name__
        acts_list.append(
            {
                "act_name": _("redis 清档: {}").format(dst_master_ip),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
        )
    if acts_list:
        sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 恢复原始cluster信息
    act_kwargs.cluster = cluster_bak

    return sub_pipeline.build_sub_process(sub_name=_("redis 备份后清档"))
