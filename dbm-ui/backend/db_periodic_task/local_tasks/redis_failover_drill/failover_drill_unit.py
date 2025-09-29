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
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from blueapps.core.celery.celery import app
from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterStatus, ClusterType
from backend.db_meta.models import Cluster

from .failover_drill import RedisFailoverDrill, RedisFailoverDrillTaskStatus
from .utils import autofix_done_polling, autofix_ticket_polling, log_with_context

TaskStatus = RedisFailoverDrillTaskStatus


def handle_drill_error(
    rfod: RedisFailoverDrill, error_info: str, task_status: str, log_level: str = "warning"
) -> None:
    log_with_context(log_level, rfod.city, error_info)
    rfod.update_drill_task_report(error_info, task_status=task_status)
    rfod.send_alert(failure_reason=error_info, task_status=task_status)


@app.task
def failover_drill_unit(city: str, conf: Dict[str, Any]) -> None:
    """
    Redis 容灾演练单元

    步骤：
    1. 屏蔽集群`cache.<cluster_name>.<biz_name>.db` [Proxy or Backend] 与DBHA服务的通信
    2. 监测 Redis 自愈发生
    3. 通过 HADBAPI 获取切换队列，确认演练目标IP发生切换
    4. 记录演练结果
    """
    drill_meta_data = {
        "bk_biz_id": conf["bk_biz_id"],
        "bk_cloud_id": conf["bk_cloud_id"],
        "labels": conf["labels"],
        "city_map": conf["city_map"],
        "instance_type": conf["target_type"],
    }

    rfod = RedisFailoverDrill(
        city=city,
        **drill_meta_data,
    )

    log_with_context("info", city, _("容灾演练资源检查"))

    cluster: Optional[Cluster] = None
    try:
        cluster = Cluster.objects.get(
            immute_domain=rfod.get_immute_domain(),
            cluster_type=ClusterType.TendisTwemproxyRedisInstance,
        )
    except Cluster.DoesNotExist:
        error_info = _("没有部署容灾演练集群，退出演练")
        handle_drill_error(rfod, error_info, TaskStatus.NO_CLUSTER)
        return
    except Exception as e:
        error_info = _("获取集群信息时发生错误: {}".format(e))
        handle_drill_error(rfod, error_info, TaskStatus.CLUSTER_ERROR)
        return

    if cluster.status != ClusterStatus.NORMAL:
        error_info = _("集群状态异常，退出演练")
        handle_drill_error(rfod, error_info, TaskStatus.ABNORMAL_CLUSTER)
        return

    # 创建容灾单据触发 DBHA
    log_with_context("info", city, _("开始触发DBHA"))
    drill_start_time = datetime.now().astimezone(timezone.utc)
    rfod.create_run_failover_drill_ticket()

    # 配置自愈和HADB API切换队列检查参数
    retry_settings = {
        "max_retries": conf["max_retry"],
        "interval": conf["interval"],
    }
    timeout_minutes = (conf["max_retry"] - 1) * conf["interval"]

    # 设置轮询限制条件
    polling_restriction = {
        "bk_biz_id": rfod.bk_biz_id,
        "cluster_id": cluster.id,
        "ip": rfod.get_drill_ip(),
        "earliest_create_allowed": drill_start_time,
    }

    autofix_generated, ticket_id = autofix_ticket_polling(polling_restriction, **retry_settings)

    dbha_info, switch_success = rfod.get_dbha_info()
    rfod.update_drill_report(dbha_info)

    switch_status_info = _("DBHA切换状态: {}").format(switch_success)
    log_with_context("info", city, switch_status_info)
    rfod.update_drill_task_report(switch_status_info)

    if autofix_generated:
        if not autofix_done_polling(ticket_id, **retry_settings):
            handle_drill_error(rfod, _("自愈结果异常"), TaskStatus.SWITCHED_AUTOFIX_ERROR)
        else:
            rfod.update_drill_task_report(switch_status_info, True, TaskStatus.SUCCESS)
    else:
        final_task_status = TaskStatus.SWITCH_FAILED if not switch_success else TaskStatus.SWITCHED_NO_AUTOFIX
        handle_drill_error(rfod, _("没有监测到Redis自愈发生, timeout: {}min".format(timeout_minutes)), final_task_status)
