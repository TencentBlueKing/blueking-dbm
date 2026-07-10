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
import pathlib
from dataclasses import asdict
from typing import Dict, List, Union

from bamboo_engine.builder import SubProcess
from django.utils.translation import gettext as _

from backend import env
from backend.db_package.models import Package
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import DeployPeripheralToolsDepart
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.act_payload.mysql.peripheraltools import PeripheralToolsPayload
from backend.flow.utils.mysql.dts.package_resolver import resolve_v2_dbbackup_package
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs


def install_dbbackup_v2_subflow(
    *,
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    exec_ips: Union[str, List[str]],
    backup_pkg: Package | None = None,
    sub_name: str | None = None,
) -> SubProcess:
    """
    安装 V2 dbbackup 程序（对齐 mysql_rollback_exercise._build_reinstall_v2_dbbackup_subflow）。

    步骤：下发 V2 备份介质 → db-actuator 部署 dbbackup 二进制（含 myloader）。
    """
    ips = [exec_ips] if isinstance(exec_ips, str) else list(exec_ips)
    pkg = backup_pkg or resolve_v2_dbbackup_package()

    sub_pipeline = SubBuilder(root_id=root_id, data=data)
    sub_pipeline.add_act(
        act_name=_("下发V2备份介质"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=ips,
                file_list=[f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{pkg.path}"],
            )
        ),
    )

    acts = []
    for ip in ips:
        acts.append(
            {
                "act_name": _("重装备份程序 {}").format(ip),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ip=[ip],
                        run_as_system_user=DBA_ROOT_USER,
                        payload_class=PeripheralToolsPayload.payload_class_path(),
                        get_mysql_payload_func=PeripheralToolsPayload.deploy_binary.__name__,
                        bk_cloud_id=bk_cloud_id,
                        cluster={
                            "departs": [DeployPeripheralToolsDepart.MySQLDBBackup],
                            "dbbackup_pkg_override": {
                                "pkg": pathlib.Path(pkg.path).name,
                                "pkg_md5": pkg.md5,
                            },
                        },
                    )
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts)
    return sub_pipeline.build_sub_process(sub_name=sub_name or _("重装 V2 备份程序"))
