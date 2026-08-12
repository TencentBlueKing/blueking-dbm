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

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mysql.common.install_dbbackup_v2_subflow import install_dbbackup_v2_subflow
from backend.flow.engine.bamboo.scene.mysql.common.mysql_restore_download_sub_flow import (
    mysql_restore_download_sub_flow,
)
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.mysql.dts.migrate.create_task import MysqlDtsCreateTaskComponent
from backend.flow.plugins.components.collections.mysql.dts.migrate.resolve_logical_backup import (
    MysqlDtsResolveLogicalBackupComponent,
)
from backend.flow.plugins.components.collections.mysql.dts.migrate.start_task import MysqlDtsStartTaskComponent
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs
from backend.flow.utils.mysql.dts.backup_helper import resolve_task_logical_backups, resolved_backup_asdict
from backend.flow.utils.mysql.dts.constants import DEFAULT_MYLOADER_PATH
from backend.flow.utils.mysql.dts.migrate_plan import (
    DtsMigratePlan,
    DtsTaskSpec,
    dts_migrate_plan_to_dict,
    dts_task_spec_to_dict,
)
from backend.ticket.builders.common.constants import MySQLBackupSource


def _collect_worker_ips(resolved_list) -> list[str]:
    ips = []
    for item in resolved_list:
        if item.dest_worker_ip and item.dest_worker_ip not in ips:
            ips.append(item.dest_worker_ip)
    return ips


def _resolve_bk_cloud_id(migrate_plan: DtsMigratePlan) -> int:
    if migrate_plan.bk_cloud_id:
        return int(migrate_plan.bk_cloud_id)
    deploy = migrate_plan.deploy_subflow_inp
    if deploy:
        return int(deploy.bk_cloud_id)
    return 0


def _add_download_acts(sub: SubBuilder, *, root_id: str, uid: str, bk_cloud_id: int, resolved_list) -> None:
    download_subflows = []
    for item in resolved_list:
        if item.backup_source == MySQLBackupSource.LOCAL.value:
            task_ids = item.local_files
            source_ip = item.backup_host
        else:
            task_ids = item.task_ids
            source_ip = None
        if not task_ids:
            raise ValueError(_("source {} 逻辑全备无可用下载文件列表").format(item.source_name))
        download_subflows.append(
            mysql_restore_download_sub_flow(
                uid=uid,
                root_id=root_id,
                bk_cloud_id=bk_cloud_id,
                file_target_path=item.myloader_dir,
                task_ids=task_ids,
                dest_ips=[item.dest_worker_ip],
                source_ip=source_ip,
            )
        )
    if len(download_subflows) == 1:
        sub.add_sub_pipeline(sub_flow=download_subflows[0])
    else:
        sub.add_parallel_sub_pipeline(sub_flow_list=download_subflows)


def mysql_dts_myloader_import_subflow(
    *,
    root_id: str,
    bk_biz_id: int,
    ticket_id: int,
    master_addr: str,
    task_spec: DtsTaskSpec,
    migrate_plan: DtsMigratePlan,
    creator: str = "",
    include_create_start: bool = True,
    deadlines_days: int = 7,
) -> SubBuilder:
    """DTS myloader 全量导入子流程：解析逻辑全备 → 装 client → 下发备份 → myloader 介质 → 建/启任务。"""
    bk_cloud_id = _resolve_bk_cloud_id(migrate_plan)
    resolved_list = resolve_task_logical_backups(
        root_id=root_id,
        migrate_plan=migrate_plan,
        sources=task_spec.sources,
        deadlines_days=deadlines_days,
    )
    worker_ips = _collect_worker_ips(resolved_list)
    if not worker_ips:
        raise ValueError(_("myloader 导入未解析到任何 DTS Worker IP"))

    flow_data = {
        "bk_biz_id": bk_biz_id,
        "ticket_id": ticket_id,
        "creator": creator,
        "created_by": creator,
        "root_id": root_id,
        "uid": str(ticket_id),
    }

    task_spec_payload = dts_task_spec_to_dict(task_spec)
    migrate_plan_payload = dts_migrate_plan_to_dict(migrate_plan)
    sub = SubBuilder(
        root_id=root_id,
        data=flow_data,
    )

    sub.add_act(
        act_name=_("解析逻辑全备"),
        act_component_code=MysqlDtsResolveLogicalBackupComponent.code,
        kwargs={
            "root_id": root_id,
            "task_spec": task_spec_payload,
            "migrate_plan": migrate_plan_payload,
            "deadlines_days": deadlines_days,
            "myloader_path": DEFAULT_MYLOADER_PATH,
            "resolved_backups": [resolved_backup_asdict(item) for item in resolved_list],
        },
    )

    sub.add_act(
        act_name=_("安装 backup_client"),
        act_component_code=DownloadBackupClientComponent.code,
        kwargs=asdict(
            DownloadBackupClientKwargs(
                bk_cloud_id=bk_cloud_id,
                bk_biz_id=bk_biz_id,
                ip_list=worker_ips,
            )
        ),
    )

    _add_download_acts(
        sub,
        root_id=root_id,
        uid=str(ticket_id),
        bk_cloud_id=bk_cloud_id,
        resolved_list=resolved_list,
    )

    sub.add_sub_pipeline(
        sub_flow=install_dbbackup_v2_subflow(
            root_id=root_id,
            data=flow_data,
            bk_cloud_id=bk_cloud_id,
            exec_ips=worker_ips,
            sub_name=_("重装 V2 备份程序"),
        )
    )

    if include_create_start:
        sub.add_act(
            act_name=_("创建 DTS 任务"),
            act_component_code=MysqlDtsCreateTaskComponent.code,
            kwargs={
                "master_addr": master_addr,
                "bk_cloud_id": int(migrate_plan.bk_cloud_id or 0),
                "task_spec": task_spec_payload,
                "migrate_plan": migrate_plan_payload,
            },
        )
        sub.add_act(
            act_name=_("启动 DTS 任务"),
            act_component_code=MysqlDtsStartTaskComponent.code,
            kwargs={
                "master_addr": master_addr,
                "bk_cloud_id": int(migrate_plan.bk_cloud_id or 0),
                "task_name": task_spec.task_name,
            },
        )

    return sub
