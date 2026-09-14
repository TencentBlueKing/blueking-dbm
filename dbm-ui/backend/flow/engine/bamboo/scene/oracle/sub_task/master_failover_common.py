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
import os
from dataclasses import asdict
from typing import Dict

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.flow.consts import DBA_ORACLE_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.oracle.sub_task.add_slave_common import BKREPO_ORACLE_PATH
from backend.flow.plugins.components.collections.oracle.exec_actuator_script import (
    ExecuteOracleActuatorScriptComponent,
)
from backend.flow.plugins.components.collections.oracle.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.oracle.upload_file import UploadFileServiceComponent
from backend.flow.utils.oracle.oracle_act_dataclass import DownloadMediaKwargs, UploadFile
from backend.flow.utils.oracle.oracle_act_payload import OracleActPayload
from backend.flow.utils.oracle.oracle_context_dataclass import MasterFailoverContext, OracleActKwargs


def build_fetch_and_dispatch_tnsnames_sub_flow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    master: str,
    slave: str,
    uid: str,
) -> SubBuilder:
    """
    获取并下发 tnsnames 文件子流程.
    包含: 从旧主获取 tnsnames -> 上传到制品库 -> 下发到新主(原备) -> 在新主合并 tnsnames.
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=data)

    sub_pipeline.add_act(
        act_name=_("获取tnsnames文件"),
        act_component_code=ExecuteOracleActuatorScriptComponent.code,
        kwargs=asdict(
            OracleActKwargs(
                exec_ip=master,
                bk_cloud_id=bk_cloud_id,
                run_as_system_user=DBA_ORACLE_USER,
                get_oracle_payload_func=OracleActPayload.get_tnsnames_file_payload.__name__,
            )
        ),
        write_payload_var=MasterFailoverContext.get_tnsnames_var_name(),
    )

    tnsnames_file = _("{}.tnsnames.ora".format(uid))

    sub_pipeline.add_act(
        act_name=_("上传tnsnames文件"),
        act_component_code=UploadFileServiceComponent.code,
        kwargs=asdict(
            UploadFile(
                path=os.path.join(BKREPO_ORACLE_PATH, tnsnames_file),
                content_var=MasterFailoverContext.get_tnsnames_var_name(),
            )
        ),
    )

    sub_pipeline.add_act(
        act_name=_("下发tnsnames文件"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=slave,
                file_list=GetFileList(db_type=DBType.Oracle).oracle_file(
                    path=BKREPO_ORACLE_PATH, filelist=[tnsnames_file]
                ),
            )
        ),
    )

    sub_pipeline.add_act(
        act_name=_("修改tnsnames文件"),
        act_component_code=ExecuteOracleActuatorScriptComponent.code,
        kwargs=asdict(
            OracleActKwargs(
                exec_ip=slave,
                bk_cloud_id=bk_cloud_id,
                run_as_system_user=DBA_ORACLE_USER,
                get_oracle_payload_func=OracleActPayload.get_merge_tnsnames_payload.__name__,
            )
        ),
    )
    return sub_pipeline.build_sub_process(sub_name=_("获取并下发tnsnames文件"))
