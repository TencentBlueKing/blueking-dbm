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
from django.utils.translation import gettext_lazy as _

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class RedisRollbackExerciseTaskStage(StrStructuredEnum):
    """
    Redis 回档演练任务状态
    """

    TASK_GENERATED = EnumField("task_generated", _("任务已生成"))
    SKIPPED = EnumField("skipped", _("已跳过"))
    BACKUP_INVALID = EnumField("backup_invalid", _("备份不可用"))

    TICKET_GEN_FAILED = EnumField("ticket_gen_failed", _("单据生成失败"))
    TICKET_GENERATED = EnumField("ticket_generated", _("单据已生成"))

    RESOURCE_APPLI_FAILED = EnumField("resource_appli_failed", _("资源申请失败"))
    RESOURCE_APPLI_SUCCEEDED = EnumField("resource_appli_succeeded", _("资源申请成功"))

    # --- Flow stages ---
    ROLLBACK_STARTED = EnumField("rollback_started", _("回档开始"))
    ROLLBACK_FAILED = EnumField("rollback_failed", _("回档失败"))
    ROLLBACK_SUCCEEDED = EnumField("rollback_succeeded", _("回档成功"))

    CLEANUP_FAILED = EnumField("cleanup_failed", _("清理失败"))

    SCENE_PRESERVED = EnumField("scene_preserved", _("现场保留待排查"))

    DONE = EnumField("done", _("已完成"))


FAILED_STAGES = [
    RedisRollbackExerciseTaskStage.BACKUP_INVALID,
    RedisRollbackExerciseTaskStage.TICKET_GEN_FAILED,
    RedisRollbackExerciseTaskStage.RESOURCE_APPLI_FAILED,
    RedisRollbackExerciseTaskStage.ROLLBACK_FAILED,
    RedisRollbackExerciseTaskStage.CLEANUP_FAILED,
    # Count as failed: weights the cluster now; DBA skip later marks a terminal failure
    RedisRollbackExerciseTaskStage.SCENE_PRESERVED,
]
