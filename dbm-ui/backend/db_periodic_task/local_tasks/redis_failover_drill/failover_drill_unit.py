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
from typing import Any, Dict, Optional, Union

from blueapps.core.celery.celery import app
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterStatus, ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.constants import FailoverDrillVersion
from backend.db_report.enums import ReportStateType
from backend.flow.utils.failover_drill_dbha import get_dbha_v2_service_ips

from .failover_drill import RedisFailoverDrill, RedisFailoverDrillTaskStatus
from .utils import autofix_done_polling, autofix_ticket_polling, log_with_context

TaskStatus = RedisFailoverDrillTaskStatus


def handle_drill_error(
    rfod: RedisFailoverDrill,
    error_info: str,
    task_status: str,
    log_level: str = "warning",
    state: str = ReportStateType.ABNORMAL,
) -> None:
    log_with_context(log_level, rfod.city, error_info)
    rfod.update_drill_task_report(error_info, state=state, task_status=task_status)
    rfod.send_alert(failure_reason=error_info, task_status=task_status)


def handle_autofix_failure(rfod: RedisFailoverDrill, error_info: str, task_status: str, switch_success: bool) -> None:
    """
    切换成功但自愈未生成或失败：v2 自愈尚未接入，记为预警；v1 维持异常
    """
    if rfod.version == FailoverDrillVersion.V2 and switch_success:
        handle_drill_error(rfod, _("{}（dbha-v2 自愈未发生）").format(error_info), task_status, state=ReportStateType.WARNING)
    else:
        handle_drill_error(rfod, error_info, task_status)


@app.task
def failover_drill_unit(target: Union[Dict[str, str], str], conf: Dict[str, Any]) -> None:
    """
    Redis 容灾演练单元

    步骤：
    1. 屏蔽演练集群 [Proxy or Backend] 与DBHA服务的通信（v2 同时停止探针）
    2. 监测 Redis 自愈发生
    3. 通过 HADBAPI 获取切换队列，确认演练目标IP发生切换
    4. 记录演练结果

    target: {"city": str, "immute_domain": str}；兼容旧消息直接传 city
    """
    if isinstance(target, str):
        target = {"city": target, "immute_domain": ""}

    drill_meta_data = {
        "bk_biz_id": conf["bk_biz_id"],
        "bk_cloud_id": conf["bk_cloud_id"],
        "labels": conf["labels"],
        "city_map": conf["city_map"],
        "instance_type": conf["target_type"],
        "version": conf.get("version") or FailoverDrillVersion.V1.value,
        "cluster_type": conf.get("cluster_type") or ClusterType.TendisTwemproxyRedisInstance.value,
    }

    rfod = RedisFailoverDrill(
        city=target["city"],
        immute_domain=target["immute_domain"],
        **drill_meta_data,
    )

    log_with_context("info", rfod.city, _("容灾演练资源检查"))

    if rfod.version == FailoverDrillVersion.V2 and not rfod.get_immute_domain():
        error_info = _("v2 容灾演练配置未指定演练集群域名(cluster_domain)，退出演练")
        handle_drill_error(rfod, error_info, TaskStatus.NO_CLUSTER_DOMAIN)
        return

    cluster: Optional[Cluster] = None
    try:
        cluster = Cluster.objects.get(**rfod.cluster_filters())
    except Cluster.DoesNotExist:
        error_info = _("没有部署容灾演练集群，或集群的业务/云区域/类型与配置不一致，退出演练")
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

    try:
        rfod.get_failover_drill_params()
    except Exception as e:
        error_info = _("获取演练目标信息时发生错误: {}".format(e))
        handle_drill_error(rfod, error_info, TaskStatus.CLUSTER_ERROR)
        return

    if rfod.version == FailoverDrillVersion.V2 and not get_dbha_v2_service_ips(
        rfod.bk_cloud_id, rfod.get_drill_logical_city_id()
    ):
        error_info = _("拿不到 dbha-v2 服务 IP，退出演练")
        handle_drill_error(rfod, error_info, TaskStatus.NO_DBHA_V2_SERVICE_IP)
        return

    # 创建容灾单据触发 DBHA
    log_with_context("info", rfod.city, _("开始触发DBHA"))
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
        "ip": rfod.get_drill_ip(),
        "earliest_create_allowed": drill_start_time,
    }

    autofix_generated, ticket_id = autofix_ticket_polling(polling_restriction, **retry_settings)

    dbha_info, switch_success = rfod.get_dbha_info()
    rfod.update_drill_report(dbha_info)

    switch_status_info = _("DBHA切换状态: {}").format(switch_success)
    log_with_context("info", rfod.city, switch_status_info)
    rfod.update_drill_task_report(switch_status_info)

    if autofix_generated and autofix_done_polling(ticket_id, **retry_settings):
        succ_info = _("自愈成功，演练正常结束")
        log_with_context("info", rfod.city, succ_info)
        rfod.update_drill_task_report(succ_info, ReportStateType.NORMAL, TaskStatus.SUCCESS)
    elif dbha_info.get("query_failed"):
        # 查不到切换队列时无法判断是否切换，不能记为"未切换"
        error_info = _("DBHA({}) 切换队列查询失败，无法判断是否切换: {}").format(rfod.version, dbha_info["error"].strip())
        handle_drill_error(rfod, error_info, TaskStatus.DBHA_QUERY_FAILED)
    elif autofix_generated:
        handle_autofix_failure(rfod, _("自愈结果异常"), TaskStatus.SWITCHED_AUTOFIX_ERROR, switch_success)
    else:
        no_autofix_info = _("没有监测到Redis自愈发生, timeout: {}min".format(timeout_minutes))
        if not switch_success:
            handle_drill_error(rfod, no_autofix_info, TaskStatus.SWITCH_FAILED)
        else:
            handle_autofix_failure(rfod, no_autofix_info, TaskStatus.SWITCHED_NO_AUTOFIX, switch_success)
