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
# 先导入注册器和工具函数，避免循环导入
from backend.db_periodic_task.local_tasks.context_manager import start_new_span  # isort:skip
from backend.db_periodic_task.local_tasks.register import register_periodic_task, registered_local_tasks  # isort:skip
from backend.db_periodic_task.constants import PeriodicTaskType  # isort:skip

# 再导入各个任务模块
from backend.db_periodic_task.local_tasks.ai_mysql_tasks.mysql_slowlog_analysis import *
from backend.db_periodic_task.local_tasks.ai_tasks.log_analysis import *
from backend.db_periodic_task.local_tasks.backup_files_expire import *
from backend.db_periodic_task.local_tasks.check_expired_job_users import *
from backend.db_periodic_task.local_tasks.clean_staging_files import *
from backend.db_periodic_task.local_tasks.db_dirty import *
from backend.db_periodic_task.local_tasks.db_meta import *
from backend.db_periodic_task.local_tasks.db_monitor import *
from backend.db_periodic_task.local_tasks.db_proxy import *
from backend.db_periodic_task.local_tasks.dbmon_heartbeat import *
from backend.db_periodic_task.local_tasks.disable_dbha import *
from backend.db_periodic_task.local_tasks.doris import *
from backend.db_periodic_task.local_tasks.es_daily_check import *
from backend.db_periodic_task.local_tasks.hdfs import *
from backend.db_periodic_task.local_tasks.iam import *
from backend.db_periodic_task.local_tasks.kafka_check import *
from backend.db_periodic_task.local_tasks.mongodb_tasks import mongodb_backup_check_task, mongodb_metric_check_task
from backend.db_periodic_task.local_tasks.mysql_autofix import *
from backend.db_periodic_task.local_tasks.mysql_backup import *
from backend.db_periodic_task.local_tasks.mysql_backup_rollback import backup_data_recovery_task
from backend.db_periodic_task.local_tasks.mysql_check_partition import *
from backend.db_periodic_task.local_tasks.mysql_checksum import check_checksum_task
from backend.db_periodic_task.local_tasks.mysql_cluster_skew import calculate_tendbcluster_skew, calculate_tendbha_skew
from backend.db_periodic_task.local_tasks.mysql_config_ai_inspect.tasks import periodic_mysql_config_ai_inspect
from backend.db_periodic_task.local_tasks.mysql_exporter_heartbeat import *
from backend.db_periodic_task.local_tasks.mysql_failover_drill import *
from backend.db_periodic_task.local_tasks.mysql_partition import *
from backend.db_periodic_task.local_tasks.randomize_password import *
from backend.db_periodic_task.local_tasks.redis_autofix import *
from backend.db_periodic_task.local_tasks.redis_backup import *
from backend.db_periodic_task.local_tasks.redis_backup_rollback import *
from backend.db_periodic_task.local_tasks.redis_clusternodes_update import *
from backend.db_periodic_task.local_tasks.redis_failover_drill import *
from backend.db_periodic_task.local_tasks.redis_tasks import *
from backend.db_periodic_task.local_tasks.sql_exec_duration_consume import *
from backend.db_periodic_task.local_tasks.sqlserver import *
from backend.db_periodic_task.local_tasks.ticket import *
from backend.db_periodic_task.local_tasks.update_host_property import sync_machine_ip_cache, update_host_property
from backend.db_periodic_task.models import DBPeriodicTask

from backend.configuration.tasks.todo_remind_tasks import send_todo_remind  # isort:skip

# 注册动态创建的定时任务
# 添加轮值排版发送定时任务
send_duty_schedule_names = [f"{db_type}_periodic_{send_duty_schedule.__name__}" for db_type in DBType.get_values()]
send_todo_remind_schedule_names = [f"dbm_periodic_{send_todo_remind.__name__}"]  # isort:skip
registered_local_tasks.update(send_duty_schedule_names)
registered_local_tasks.update(send_todo_remind_schedule_names)  # isort:skip

# 删除过期的本地周期任务
DBPeriodicTask.delete_legacy_periodic_task(registered_local_tasks, PeriodicTaskType.LOCAL.value)
