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
import logging
from datetime import datetime, timezone

from blueapps.core.celery.celery import app
from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterStatus, ClusterType
from backend.db_meta.models import Cluster

from .failover_drill import RedisFailoverDrill
from .utils import autofix_ticket_polling

logger = logging.getLogger("celery")


@app.task
def failover_drill_unit(city: str, conf: dict):
    """
    Redis 容灾演练单元

    步骤：
    1. 屏蔽集群`failover.<cluster_name>.dbatest.db` [Proxy or Backend] 与DBHA服务的通信
    2. 监测 Redis 自愈发生
    3. 通过 HADBAPI 获取切换队列，确认演练目标IP发生切换
    4. 记录演练结果
    """
    meta_data = {
        "bk_biz_id": conf["bk_biz_id"],
        "bk_cloud_id": conf["bk_cloud_id"],
        "labels": conf["labels"],
        "city_map": conf["city_map"],
    }

    rfod = RedisFailoverDrill(
        city=city,
        **meta_data,
    )

    logger.info(_("容灾演练资源检查"))
    cluster = None
    try:
        cluster = Cluster.objects.get(
            immute_domain=rfod.get_immute_domain(),
            cluster_type=ClusterType.TendisTwemproxyRedisInstance,
        )
    except Cluster.DoesNotExist:
        info = _("City: {} 没有部署容灾演练集群，退出演练".format(city))
        logger.warning(info)
        rfod.update_drill_report(info)
        return
    except Exception as e:
        info = _("获取集群信息时发生错误: {}".format(e))
        logger.error(info)
        rfod.update_drill_report(info)
        return

    if cluster.status != ClusterStatus.NORMAL:
        info = _("集群状态异常，退出演练 City: {}".format(city))
        logger.error(info)
        rfod.update_drill_report(info)
        return

    # 创建容灾单据触发 DBHA
    logger.info(_("开始触发DBHA"))
    start_time = datetime.now().astimezone(timezone.utc)
    rfod.create_run_failover_drill_ticket(conf["target_type"])

    # 自愈 和 HADB API 切换队列检查
    retry_settings = {
        "max_retries": conf["max_retry"],
        "interval": conf["interval"],
    }
    timeout = conf["max_retry"] * conf["interval"]
    restriction = {
        "bk_biz_id": rfod.bk_biz_id,
        "cluster_id": cluster.id,
        "ip": rfod.get_drill_ip(),
        "earliest_create_allowed": start_time,
    }
    if not autofix_ticket_polling(restriction, **retry_settings):
        info = _("没有监测到Redis自愈发生, Timeout: {}min, City: {}".format(timeout, city))
        logger.warning(info)
        rfod.update_drill_report(info)

    info = _("Redis容灾演练执行完毕 City: {}".format(city))
    dbha_info, dbha_status, is_succ = rfod.get_dbha_info()
    rfod.update_drill_report(info, dbha_info, is_succ, dbha_status)
    logger.info(info)
