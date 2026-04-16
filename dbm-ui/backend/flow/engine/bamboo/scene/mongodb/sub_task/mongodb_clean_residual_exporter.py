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
from pathlib import Path
from typing import List

from django.utils.translation import gettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.flow.consts import MongoDBActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.mongodb.mongodb_install_dbmon import get_pkg_info
from backend.flow.engine.bamboo.scene.mongodb.sub_task.send_media import SendMedia
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job2 import ExecJobComponent2
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs, CommonContext


def gse_agent_base_dir_from_beat_path() -> str:
    """
    由 env.MYSQL_CROND_BEAT_PATH（与 install_dbmon 中 bkmonitorbeat 路径一致，默认 .../plugins/bin/bkmonitorbeat）
    解析 GSE Agent 安装根目录。
    """
    beat_path = env.MYSQL_CROND_BEAT_PATH
    try:
        p = Path(str(beat_path).strip())
        if p.is_absolute() and len(p.parents) >= 3:
            return str(p.parents[2])
    except (OSError, ValueError, TypeError):
        pass
    raise ValueError(f"Failed to parse GSE Agent base dir from beat path: {beat_path}")


def add_mongodb_clean_residual_exporter_acts(
    p: Builder, db_type: str, bk_cloud_id: int, bk_biz_id: int, iplist: List[str]
) -> None:
    """
    SA 空闲检查前：在同一子流程中顺序执行「下发 MongoDB actuator」与「mongodb_clean_residual_exporter」。
    使用 iplist 执行清理任务，统一使用传入的 bk_cloud_id。
    """
    if db_type != DBType.MongoDB:
        return
    if not iplist:
        return

    exec_ip = list(iplist)
    bk_host_list = [{"ip": ip, "bk_cloud_id": bk_cloud_id} for ip in iplist]

    act_kwargs = ActKwargs()
    act_kwargs.payload = {"bk_biz_id": bk_biz_id}
    act_kwargs.get_file_path()

    pkg_info = get_pkg_info()
    actuator_file_list = [
        "{}/{}/{}".format(env.BKREPO_PROJECT, env.BKREPO_BUCKET, pkg_info["actuator_pkg"].path),
    ]

    sub_p = SubBuilder(root_id=p.root_id, data=p.data)
    sub_p.add_act(
        **SendMedia.act(
            act_name=_("MongoDB-下发 actuator"),
            file_list=actuator_file_list,
            bk_host_list=bk_host_list,
            file_target_path=act_kwargs.file_path,
        )
    )
    sub_p.add_act(
        act_name=_("MongoDB-清理 exporter 残留"),
        act_component_code=ExecJobComponent2.code,
        kwargs={
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": bk_cloud_id,
            "exec_ip": exec_ip,
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.CleanResidualExporter,
                "file_path": act_kwargs.file_path,
                "payload": {
                    "base_dir": gse_agent_base_dir_from_beat_path(),
                    "exporter_name": "dbm_mongodb_exporter",
                    "sudo_account": "root",
                    "exec_account": "root",
                    "dry_run": False,
                },
            },
        },
    )
    p.add_sub_pipeline(sub_p.build_sub_process(sub_name=_("MongoDB-exporter残留清理")))
