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
from celery.schedules import crontab

from backend import env
from backend.db_periodic_task.constants import GET_AND_DELETE_SET_LUA
from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.dbm_aiagent.agent.constants import FLOW_LOG_AI_ANALYSIS_KEY
from backend.utils.redis import RedisConn

# worker 加载 CELERY_IMPORTS 时执行。ai的异步任务不在自动发现路径上，
# 只在投递函数内部导入的话，其他 worker 进程会把消息当成未注册任务丢弃。
if env.ENABLE_DBM_AI:
    import backend.dbm_aiagent.agent.services.log_analysis.tasks  # noqa: F401


@register_periodic_task(run_every=crontab(minute="*"))
def periodic_pipeline_log_ai_analysis():
    """周期任务错误日志AI分析"""
    if not env.ENABLE_DBM_AI:
        return

    from backend.dbm_aiagent.agent.services.log_analysis.tasks import pipeline_log_ai_analysis

    script = RedisConn.register_script(GET_AND_DELETE_SET_LUA)
    task_list = script(keys=[FLOW_LOG_AI_ANALYSIS_KEY])
    for root_id in task_list:
        pipeline_log_ai_analysis.apply_async(args=(root_id,))
