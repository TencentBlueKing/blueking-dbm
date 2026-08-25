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
from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_catchup_cutover_subflow import (
    mysql_dts_catchup_cutover_subflow,
)
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_myloader_import_subflow import (
    mysql_dts_myloader_import_subflow,
)
from backend.flow.plugins.components.collections.mysql.dts.migrate.create_task import MysqlDtsCreateTaskComponent
from backend.flow.plugins.components.collections.mysql.dts.migrate.poll_full_load import MysqlDtsPollFullLoadComponent
from backend.flow.plugins.components.collections.mysql.dts.migrate.register_source import (
    MysqlDtsRegisterSourceComponent,
)
from backend.flow.plugins.components.collections.mysql.dts.migrate.start_task import MysqlDtsStartTaskComponent
from backend.flow.plugins.components.collections.mysql.dts.migrate.update_meta import MysqlDtsUpdateMetaComponent
from backend.flow.utils.mysql.dts.constants import (
    MYSQL_DTS_FULL_LOAD_MAX_FAIL_STREAK,
    MYSQL_DTS_FULL_LOAD_POLL_INTERVAL,
    FullLoadEngine,
)
from backend.flow.utils.mysql.dts.migrate_helper import plan_deploy_cluster_name
from backend.flow.utils.mysql.dts.migrate_plan import (
    DtsMigratePlan,
    DtsTaskSpec,
    dts_migrate_plan_to_dict,
    dts_task_spec_to_dict,
)


def _use_myloader_engine(task_spec: DtsTaskSpec, migrate_plan: DtsMigratePlan) -> bool:
    engine = task_spec.dts_task_config.full_load_engine or migrate_plan.dts_task_config.full_load_engine
    return engine == FullLoadEngine.MYLOADER.value


def _resolve_task_mode(task_spec: DtsTaskSpec, migrate_plan: DtsMigratePlan) -> str:
    return task_spec.dts_task_config.task_mode or migrate_plan.dts_task_config.task_mode or "all"


def mysql_dts_migrate_task_subflow(
    *,
    root_id: str,
    bk_biz_id: int,
    ticket_id: int,
    master_addr: str,
    task_spec: DtsTaskSpec,
    migrate_plan: DtsMigratePlan,
    creator: str = "",
    dts_user: str = "",
    dts_password: str = "",
    need_checksum: bool = True,
) -> SubBuilder:
    """单 DTS Task：注册启动 → 写元数据 → 追平/校验/安全切换。

    注意：Act kwargs 只能放 JSON 可序列化结构；DtsTaskSpec / DtsMigratePlan
    必须先 to_dict，组件侧再 hydrate（同 Ticket.details 禁放 dataclass 规则）。
    """
    task_spec_payload = dts_task_spec_to_dict(task_spec)
    migrate_plan_payload = dts_migrate_plan_to_dict(migrate_plan)
    bk_cloud_id = int(migrate_plan.bk_cloud_id or 0)
    cluster_name = plan_deploy_cluster_name(migrate_plan)
    sub = SubBuilder(
        root_id=root_id,
        data={
            "bk_biz_id": bk_biz_id,
            "ticket_id": ticket_id,
            "uid": ticket_id,
            "creator": creator,
            "created_by": creator,
            "root_id": root_id,
            "task_name": task_spec.task_name,
            "dts_task_ids": [task_spec.task_name] if task_spec.task_name else [],
        },
    )

    sub.add_act(
        act_name=_("注册 DTS Source"),
        act_component_code=MysqlDtsRegisterSourceComponent.code,
        kwargs={
            "master_addr": master_addr,
            "bk_cloud_id": bk_cloud_id,
            "task_spec": task_spec_payload,
            "migrate_type": migrate_plan.migrate_type,
            "dts_user": dts_user,
            "dts_password": dts_password,
        },
    )

    if _use_myloader_engine(task_spec, migrate_plan):
        # myloader：全备下发 + 介质就绪 + create/start
        sub.add_sub_pipeline(
            sub_flow=mysql_dts_myloader_import_subflow(
                root_id=root_id,
                bk_biz_id=bk_biz_id,
                ticket_id=ticket_id,
                master_addr=master_addr,
                task_spec=task_spec,
                migrate_plan=migrate_plan,
                creator=creator,
                include_create_start=True,
            ).build_sub_process(sub_name=_("myloader 全量导入并建启任务"))
        )
    else:
        sub.add_act(
            act_name=_("创建 DTS 任务"),
            act_component_code=MysqlDtsCreateTaskComponent.code,
            kwargs={
                "master_addr": master_addr,
                "bk_cloud_id": bk_cloud_id,
                "task_spec": task_spec_payload,
                "migrate_plan": migrate_plan_payload,
                "dts_user": dts_user,
                "dts_password": dts_password,
                "cluster_name": cluster_name,
            },
        )
        sub.add_act(
            act_name=_("启动 DTS 任务"),
            act_component_code=MysqlDtsStartTaskComponent.code,
            kwargs={
                "master_addr": master_addr,
                "bk_cloud_id": bk_cloud_id,
                "task_name": task_spec.task_name,
            },
        )

    sub.add_act(
        act_name=_("写入迁移元数据"),
        act_component_code=MysqlDtsUpdateMetaComponent.code,
        kwargs={
            "bk_biz_id": bk_biz_id,
            "ticket_id": ticket_id,
            "root_id": root_id,
            "task_spec": task_spec_payload,
            "migrate_type": migrate_plan.migrate_type,
            "migrate_topology": migrate_plan.topology,
            "task_name": task_spec.task_name,
            "dts_cluster_id": migrate_plan.dts_cluster_id,
            "cluster_name": cluster_name,
            "creator": creator,
        },
    )
    # builtin：update_meta 后等待全量越过 Dump/Load，再进入追平（myloader 已由导入子流程保障）
    if not _use_myloader_engine(task_spec, migrate_plan):
        sub.add_act(
            act_name=_("等待 DTS 全量导入完成"),
            act_component_code=MysqlDtsPollFullLoadComponent.code,
            kwargs={
                "master_addr": master_addr,
                "bk_cloud_id": bk_cloud_id,
                "task_name": task_spec.task_name,
                "source_name_list": [s.source_name for s in task_spec.sources if s.source_name] or None,
                "task_mode": _resolve_task_mode(task_spec, migrate_plan),
                "poll_interval": MYSQL_DTS_FULL_LOAD_POLL_INTERVAL,
                "max_fail_streak": MYSQL_DTS_FULL_LOAD_MAX_FAIL_STREAK,
            },
        )
    # 追平 → 数据校验 → Pause/cutover（不做域名切换）
    sub.add_sub_pipeline(
        sub_flow=mysql_dts_catchup_cutover_subflow(
            root_id=root_id,
            bk_biz_id=bk_biz_id,
            ticket_id=ticket_id,
            master_addr=master_addr,
            task_spec=task_spec,
            migrate_plan=migrate_plan,
            dts_user=dts_user,
            dts_password=dts_password,
            creator=creator,
            need_checksum=need_checksum,
        ).build_sub_process(sub_name=_("追平校验并安全切换"))
    )
    return sub
