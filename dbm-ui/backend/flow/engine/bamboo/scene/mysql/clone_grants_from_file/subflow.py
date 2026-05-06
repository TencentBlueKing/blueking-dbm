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
import copy
import logging
import os
import uuid
from dataclasses import asdict
from typing import Dict

from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.configuration.constants import DBType
from backend.db_meta.enums import MachineType
from backend.db_meta.models import Machine
from backend.flow.consts import DBA_ROOT_USER, LONG_JOB_TIMEOUT, DBActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder, SubProcess
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.clone_grants_from_file.payload.payload import CloneGrantsFromFilePayload
from backend.flow.plugins.components.collections.mysql.clone_grants_from_file.version_check import (
    CloneGrantsVersionCheckComponent,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent as MySQLTransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs, P2PFileKwargs

logger = logging.getLogger("flow")


def clone_grants_from_file_subflow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    bk_biz_id: int,
    source_address: str,
    dest_addresses: list[str],
    run_as_system_user: str = DBA_ROOT_USER,
) -> SubProcess:
    source_ip, source_port = source_address.split(":")
    dest_ips = list({addr.split(":")[0] for addr in dest_addresses})
    all_ips = list({source_ip, *dest_ips})

    backup_id = uuid.uuid1().__str__()
    source_priv_file_name = f"source_priv_{backup_id}_{source_ip}_{source_port}.priv"
    source_priv_file_path = os.path.join("/data/dbbak", source_priv_file_name)

    is_spider = Machine.objects.get(ip=source_ip, bk_cloud_id=bk_cloud_id).machine_type == MachineType.SPIDER.value

    try:
        res = DRSApi.rpc(
            {
                "addresses": [source_address],
                "cmds": ["select @@version as version"],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            logger.error(f"check source version failed: {res[0]['error_msg']}")
            raise Exception(f"{res[0]['error_msg']}")
        if res[0]["cmd_results"][0]["error_msg"]:
            logger.error(f"check source version failed: {res[0]['cmd_results'][0]['error_msg']}")
            raise Exception(f"{res[0]['cmd_results'][0]['error_msg']}")

        source_raw_version = res[0]["cmd_results"][0]["table_data"][0]["version"]
        logger.info(f"source raw version: {source_raw_version}")
    except Exception as e:  # noqa
        raise Exception(f"check source version failed: {e}") from e

    pipe = SubBuilder(root_id=root_id, data=data)

    pipe.add_act(
        act_name=_("版本号检查"),
        act_component_code=CloneGrantsVersionCheckComponent.code,
        kwargs={
            "source_raw_version": source_raw_version,
            "dest_addresses": dest_addresses,
            "bk_cloud_id": bk_cloud_id,
            "is_spider": is_spider,
        },
    )

    pipe.add_act(
        act_name=_("下发 dbactuator"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=all_ips,
                file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                run_as_system_user=run_as_system_user,
            )
        ),
    )

    pipe.add_act(
        act_name=_("在 {} 备份权限".format(source_address)),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                job_timeout=LONG_JOB_TIMEOUT,
                bk_cloud_id=bk_cloud_id,
                run_as_system_user=run_as_system_user,
                exec_ip=source_ip,
                payload_class=CloneGrantsFromFilePayload.payload_class_path(),
                get_mysql_payload_func=CloneGrantsFromFilePayload.dump_priv_on_source.__name__,
                cluster={
                    "port": source_port,
                    "ip": source_ip,
                    "backup_id": backup_id,
                    "source_priv_file_path": source_priv_file_path,
                },
            )
        ),
    )

    pipe.add_act(
        act_name=_("分发备份文件到 {}".format(dest_ips)),
        act_component_code=MySQLTransFileComponent.code,
        kwargs=asdict(
            P2PFileKwargs(
                bk_cloud_id=bk_cloud_id,
                file_list=[source_priv_file_path],
                file_target_path="/data/dbbak",
                source_ip_list=[source_ip],
                exec_ip=dest_ips,
                run_as_system_user=run_as_system_user,
            )
        ),
    )

    on_dest_subflows = []

    for dest_address in dest_addresses:
        dest_ip, dest_port = dest_address.split(":")
        on_dest_subflow = SubBuilder(root_id=root_id, data=copy.deepcopy(data))
        for action in [
            DBActuatorActionEnum.CloneGrantsParseFile,
            DBActuatorActionEnum.CloneGrantsPrecheckCreate,
            DBActuatorActionEnum.CloneGrantsImportCreate,
            DBActuatorActionEnum.CloneGrantsVerifyCreate,
            DBActuatorActionEnum.CloneGrantsImportGrant,
            DBActuatorActionEnum.CloneGrantsVerifyGrant,
        ]:
            on_dest_subflow.add_act(
                act_name=str(DBActuatorActionEnum.get_choice_label(action)),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        job_timeout=LONG_JOB_TIMEOUT,
                        bk_cloud_id=bk_cloud_id,
                        run_as_system_user=run_as_system_user,
                        exec_ip=dest_ip,
                        payload_class=CloneGrantsFromFilePayload.payload_class_path(),
                        get_mysql_payload_func=CloneGrantsFromFilePayload.on_dest.__name__,
                        cluster={
                            "source_ip": source_ip,
                            "source_port": source_port,
                            "dest_port": dest_port,
                            "source_priv_file_path": source_priv_file_path,
                            "source_raw_version": source_raw_version,
                            "action": action.value,
                            "is_spider": is_spider,
                        },
                    )
                ),
            )

        on_dest_subflows.append(on_dest_subflow.build_sub_process(sub_name=_("在 {} 恢复权限".format(dest_address))))

    pipe.add_parallel_sub_pipeline(on_dest_subflows)
    return pipe.build_sub_process(sub_name=_("克隆 {} 的权限到 {}".format(source_address, dest_addresses)))
