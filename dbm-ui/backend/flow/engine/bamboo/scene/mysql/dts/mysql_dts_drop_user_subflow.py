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
from backend.flow.utils.mysql.dts.context import MysqlDtsDropUserSubflowInput
from backend.flow.utils.mysql.dts.migrate_credentials import build_dts_drop_user_parallel_acts


def mysql_dts_drop_user_subflow(inp: MysqlDtsDropUserSubflowInput) -> SubBuilder:
    """删除 DTS 迁移临时账号子流程。

    并行调用通用 DropUserComponent，DROP USER `dts_user`@`grant_host`。

    挂载点：
      1. 成功路径：mysql_dts_task_clean_subflow（总流程末尾节点 dts-task-clean）内挂载本子流程
      2. 终止路径：Signal REVOKED（终止任务）由 mysql_dts_migrate_handler 同步尽力 DROP
         （不跑本子流程，逻辑与 DropUserComponent / ignore_errors 对齐）

    不要挂：DESTROY cleanup（mysql_dts_cleanup_subflow）；也不要仅在 migrate_subflow 末尾硬挂
    作为唯一成功路径（成功清理应走可扩展 dts-task-clean）。

    入参：直接组装 MysqlDtsDropUserSubflowInput（与 add_user 同源凭证）。
    """
    sub = SubBuilder(
        root_id=inp.root_id,
        data={
            "bk_biz_id": inp.bk_biz_id,
            # add_parallel_acts 硬取 data["uid"]；本子流程无 ticket_id，回退用 root_id
            "uid": inp.root_id,
            "creator": inp.creator,
            "created_by": inp.creator,
            "root_id": inp.root_id,
        },
    )
    acts = build_dts_drop_user_parallel_acts(
        dts_user=inp.dts_user,
        grant_hosts=inp.grant_hosts,
        grant_targets=inp.grant_targets,
        ignore_errors=inp.ignore_errors,
    )
    if not acts:
        raise ValueError(_("无法组装删除临时账号节点：grant_hosts/grant_targets 无效"))
    sub.add_parallel_acts(acts_list=acts)
    return sub
