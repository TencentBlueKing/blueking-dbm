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

from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.revoke.base import RevokeFlowBase
from backend.flow.plugins.components.collections.redis.redis_rollback_exercise import (
    RedisExerciseBestEffortCleanupComponent,
    RedisExerciseRevokeAppliedHostsComponent,
)
from backend.flow.utils.redis.redis_context_dataclass import RedisRollbackExerciseContext


class RedisRollbackExerciseRevokeFlow(RevokeFlowBase):
    """Cleanup flow used by RECYCLE_APPLY_HOST after rollback exercise ticket termination."""

    def revoke_flow(self):
        ticket_data = copy.deepcopy(self.data)
        if ticket_data.get("parent_ticket"):
            ticket_data["uid"] = ticket_data["parent_ticket"]

        revoke_pipeline = Builder(root_id=self.root_id, data=ticket_data)
        revoke_pipeline.add_act(
            act_name=_("最佳尝试清理回档演练临时资源"),
            act_component_code=RedisExerciseBestEffortCleanupComponent.code,
            kwargs={"set_trans_data_dataclass": RedisRollbackExerciseContext.__name__},
            error_ignorable=True,
        )
        revoke_pipeline.add_act(
            act_name=_("输出回档演练待退回资源主机"),
            act_component_code=RedisExerciseRevokeAppliedHostsComponent.code,
            kwargs={"set_trans_data_dataclass": RedisRollbackExerciseContext.__name__},
        )
        revoke_pipeline.run_pipeline(init_trans_data_class=RedisRollbackExerciseContext())
