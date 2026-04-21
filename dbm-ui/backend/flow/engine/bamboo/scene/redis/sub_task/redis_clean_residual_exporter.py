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

from dataclasses import asdict
from pathlib import Path
from typing import List

from django.utils.translation import gettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.flow.consts import ConfigDefaultEnum, RedisActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_job2 import RedisExecJobComponent2
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext


def gse_agent_base_dir_from_beat_path() -> str:
    """
    由 env.MYSQL_CROND_BEAT_PATH（与 install_dbmon 中 bkmonitorbeat 路径一致）解析 GSE Agent 安装根目录。

    MYSQL_CROND_BEAT_PATH 必须为非空字符串，且为绝对路径，且至少包含三层父路径（取 parents[2] 作为 agent 根）。
    配置错误或无法解析时抛出 ValueError。
    """
    beat_path = env.MYSQL_CROND_BEAT_PATH
    if not str(beat_path).strip():
        raise ValueError("MYSQL_CROND_BEAT_PATH is required and must not be empty")
    try:
        p = Path(str(beat_path).strip())
        if p.is_absolute() and len(p.parents) >= 3:
            return str(p.parents[2])
    except (OSError, ValueError, TypeError):
        pass
    raise ValueError(f"Failed to parse GSE Agent base dir from beat path: {beat_path}")


def add_redis_clean_residual_exporter_acts(
    p: Builder, db_type: str, bk_cloud_id: int, bk_biz_id: int, iplist: List[str]
) -> None:
    """
    SA 空闲检查前：在同一子流程中顺序执行「下发 Redis actuator」与「redis_clean_residual_exporter」。
    使用 iplist 执行清理任务，统一使用传入的 bk_cloud_id。
    """
    if db_type != DBType.Redis:
        return
    if not iplist:
        return

    base_dir = gse_agent_base_dir_from_beat_path()

    trans_files = GetFileList(db_type=DBType.Redis)
    act_kwargs = ActKwargs()
    act_kwargs.set_trans_data_dataclass = CommonContext.__name__
    act_kwargs.file_list = trans_files.get_db_actuator_package()
    act_kwargs.bk_cloud_id = bk_cloud_id
    act_kwargs.exec_ip = list(iplist)

    sub_p = SubBuilder(root_id=p.root_id, data=p.data)
    sub_p.add_act(
        act_name=_("Redis-下发 actuator"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(act_kwargs),
    )
    sub_p.add_act(
        act_name=_("Redis-清理 exporter 残留"),
        act_component_code=RedisExecJobComponent2.code,
        kwargs={
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": bk_cloud_id,
            "exec_ip": list(iplist),
            "db_act_template": {
                "action": RedisActuatorActionEnum.CLEAN_RESIDUAL_EXPORTER.value,
                "exec_account": "root",
                "sudo_account": "root",
                "file_path": ConfigDefaultEnum.DATA_DIRS[0],
                "payload": {
                    "base_dir": base_dir,
                    "exporter_names": [
                        "dbm_redis_exporter",
                        "dbm_predixy_exporter",
                        "dbm_twemproxy_exporter",
                    ],
                    "bk_biz_id": bk_biz_id,
                    "dry_run": False,
                },
            },
        },
    )
    p.add_sub_pipeline(sub_p.build_sub_process(sub_name=_("Redis-exporter残留清理")))
