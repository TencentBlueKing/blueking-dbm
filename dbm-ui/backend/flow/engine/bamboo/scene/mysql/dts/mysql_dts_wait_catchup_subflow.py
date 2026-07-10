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
from backend.flow.plugins.components.collections.mysql.dts.migrate.poll_catchup import MysqlDtsPollCatchupComponent
from backend.flow.utils.mysql.dts.constants import (
    MYSQL_DTS_CATCHUP_MAX_FAIL_STREAK,
    MYSQL_DTS_CATCHUP_POLL_INTERVAL,
    MYSQL_DTS_CATCHUP_REQUIRED_CONSECUTIVE,
)
from backend.flow.utils.mysql.dts.context import MysqlDtsWaitCatchupSubflowInput


def mysql_dts_wait_catchup_subflow(inp: MysqlDtsWaitCatchupSubflowInput) -> SubBuilder:
    """等待 DTS 增量追平（Flow 内嵌 schedule 轮询，非 Celery）。"""
    sub = SubBuilder(
        root_id=inp.root_id,
        data={
            "bk_biz_id": inp.bk_biz_id,
            "uid": inp.root_id,
            "creator": inp.creator,
            "created_by": inp.creator,
            "root_id": inp.root_id,
        },
    )
    sub.add_act(
        act_name=_("轮询等待 DTS 追平"),
        act_component_code=MysqlDtsPollCatchupComponent.code,
        kwargs={
            "master_addr": inp.master_addr,
            "task_name": inp.task_name,
            "source_name_list": inp.source_name_list,
            "poll_interval": inp.poll_interval or MYSQL_DTS_CATCHUP_POLL_INTERVAL,
            "required_consecutive": inp.required_consecutive or MYSQL_DTS_CATCHUP_REQUIRED_CONSECUTIVE,
            "max_fail_streak": inp.max_fail_streak or MYSQL_DTS_CATCHUP_MAX_FAIL_STREAK,
        },
    )
    return sub
