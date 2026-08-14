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

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.dts.migrate.cutover_meta import MysqlDtsCutoverMetaComponent
from backend.flow.plugins.components.collections.mysql.dts.migrate.poll_confirm_alive import (
    MysqlDtsPollConfirmAliveComponent,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.dts.context import MysqlDtsCutoverSubflowInput, MysqlDtsTransData
from backend.flow.utils.mysql.dts.cutover_helper import build_dts_cutover_payload, resolve_dts_master_exec_target
from backend.flow.utils.mysql.dts.migrate_helper import task_mode_runs_incremental
from backend.flow.utils.mysql.dts.migrate_plan import DtsMigratePlan, DtsTaskSpec
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload


def mysql_dts_cutover_subflow(
    *,
    inp: MysqlDtsCutoverSubflowInput,
    task_spec: DtsTaskSpec,
    migrate_plan: DtsMigratePlan,
    dts_user: str,
    dts_password: str,
    checksum_passed: bool = False,
    skip_checksum: bool = False,
) -> SubBuilder:
    """确认（增量带存活轮询）→ 下发 dbactuator → dts-cutover → 写终态/位点。不做域名切换。"""
    sub = SubBuilder(
        root_id=inp.root_id,
        data={
            "bk_biz_id": inp.bk_biz_id,
            "uid": inp.ticket_id,
            "ticket_id": inp.ticket_id,
            "creator": inp.creator,
            "created_by": inp.creator,
            "root_id": inp.root_id,
        },
    )

    exec_target = resolve_dts_master_exec_target(migrate_plan, inp.master_addr)
    cutover_extend = build_dts_cutover_payload(
        master_addr=inp.master_addr,
        deploy_path=inp.deploy_path,
        task_name=inp.task_name,
        task_spec=task_spec,
        dts_user=dts_user,
        dts_password=dts_password,
        checksum_passed=checksum_passed,
        skip_checksum=skip_checksum,
    )

    task_mode = task_spec.dts_task_config.task_mode or migrate_plan.dts_task_config.task_mode or "all"
    confirm_name = _("增量同步中/确认切换（不切换域名）")
    if task_mode_runs_incremental(task_mode):
        sub.add_act(
            act_name=confirm_name,
            act_component_code=MysqlDtsPollConfirmAliveComponent.code,
            kwargs={
                "master_addr": inp.master_addr,
                "bk_cloud_id": int(migrate_plan.bk_cloud_id or 0),
                "task_name": inp.task_name,
                "source_name_list": [s.source_name for s in task_spec.sources if s.source_name] or None,
            },
        )
    else:
        sub.add_act(
            act_name=confirm_name,
            act_component_code=PauseComponent.code,
            kwargs={},
        )
    sub.add_act(
        act_name=_("下发 db-actuator 到 DTS Master"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=exec_target["bk_cloud_id"],
                exec_ip=exec_target["ip"],
                file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
            )
        ),
    )
    sub.add_act(
        act_name=_("执行 DTS 安全切换（源表锁 + Master API stop）"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                bk_cloud_id=exec_target["bk_cloud_id"],
                exec_ip=exec_target["ip"],
                run_as_system_user=DBA_ROOT_USER,
                get_mysql_payload_func=MysqlActPayload.get_dts_cutover_payload.__name__,
                cluster={"dts_cutover": cutover_extend},
            )
        ),
        write_payload_var=MysqlDtsTransData.get_cutover_position_var_name(),
    )
    sub.add_act(
        act_name=_("更新迁移元数据为已断开"),
        act_component_code=MysqlDtsCutoverMetaComponent.code,
        kwargs={
            "ticket_id": inp.ticket_id,
            "task_name": inp.task_name,
            # 位点由上游 actuator write_payload_var → trans_data.cutover_position 注入
        },
    )
    return sub
