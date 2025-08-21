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

from blueapps.core.celery.celery import app
from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.exceptions import DBMetaException

from ...models import FailoverDrillConfig
from .cluster_apply_destroy import cluster_status_polling, flow_status_polling
from .failover_drill import MysqlFailoverDrill
from .failover_drill_spider import TendbclusterFailoverDrill

logger = logging.getLogger("celery")


@app.task
def ha_failover_drill_unit(city: str):
    try:
        conf = FailoverDrillConfig.objects.get(cluster_type=ClusterType.TenDBHA.value)
    except Exception as e:
        raise DBMetaException(message="failover drill configuration error.{}".format(e))

    if not conf.switch_flag:
        logger.info(_("容灾演练配置关闭"))
        return

    bk_biz_id = conf.bk_biz_id
    bk_cloud_id = conf.bk_cloud_id
    db_module_id = conf.db_module_id
    labels = conf.labels
    city_map = conf.city_map
    max_retry = conf.max_retry
    interval = conf.interval

    mfod = MysqlFailoverDrill(
        city=city,
        labels=labels,
        bk_biz_id=bk_biz_id,
        bk_cloud_id=bk_cloud_id,
        db_module_id=db_module_id,
        city_map=city_map,
    )

    logger.info(_("资源申请"))
    mfod.apply_ha_resource()

    logger.info(_("上架集群"))
    mfod.ha_cluster_apply()

    logger.info(_("轮询集群上架单据状态"))
    if flow_status_polling(root_id=mfod.apply_root_id, max_retry=max_retry, interval=interval):
        logger.info(_("开始触发dbha！"))
        mfod.create_run_failover_drill_ticket()
    else:
        # 先打印日志，后续记录到表里
        info = _("Failover drill failed when applying the cluster! root_id: {}".format(mfod.apply_root_id))
        logger.error(info)
        mfod.update_drill_report(info)
        return

    if not cluster_status_polling(mfod.get_immute_domain()[0], max_retry, interval):
        info = _("集群状态没变，dbha切换可能没成功，请检查！")
        logger.info(info)
        mfod.update_drill_report(info)

    logger.info(_("开始禁用集群"))
    mfod.ha_cluster_disable()
    if not flow_status_polling(mfod.disable_root_id, max_retry=max_retry, interval=interval):
        info = _("集群禁用失败，请检查！")
        logger.info(info)
        mfod.update_drill_report(info)
        return

    logger.info(_("集群禁用单据成功执行！开始下架集群"))
    mfod.ha_cluster_destroy()
    if not flow_status_polling(mfod.destroy_root_id, max_retry=max_retry, interval=interval):
        info = _("集群下架失败，请检查！")
        logger.info(info)
        mfod.update_drill_report(info)
        return

    logger.info(_("集群下架单据成功执行！开始资源重新导进资源池！"))
    mfod.reimport_ha_resource()
    info = _("容灾演练执行成功！")
    logger.info(info)
    dbha_info, dbha_status = mfod.get_dbha_info()
    mfod.update_drill_report(info, dbha_info, True, dbha_status)


@app.task
def spider_failover_drill_unit(city: str):
    """
    异步任务，完整的容灾流程（上架、容灾演练、下架）
    @param info:
    @return:
    """
    try:
        conf = FailoverDrillConfig.objects.get(cluster_type=ClusterType.TenDBCluster.value)
    except Exception as e:
        raise DBMetaException(message=_("failover drill configuration error.{}".format(e)))

    if not conf.switch_flag:
        logger.info(_("容灾演练配置关闭"))
        return

    bk_biz_id = conf.bk_biz_id
    bk_cloud_id = conf.bk_cloud_id
    db_module_id = conf.db_module_id
    labels = conf.labels
    city_map = conf.city_map
    max_retry = conf.max_retry
    interval = conf.interval

    sfod = TendbclusterFailoverDrill(
        city=city,
        labels=labels,
        bk_biz_id=bk_biz_id,
        bk_cloud_id=bk_cloud_id,
        db_module_id=db_module_id,
        city_map=city_map,
    )

    logger.info(_("资源申请"))
    sfod.apply_ha_resource()

    logger.info(_("上架集群"))
    sfod.tendbcluster_cluster_apply()

    logger.info(_("轮询集群上架单据状态"))
    if flow_status_polling(root_id=sfod.apply_root_id, max_retry=max_retry, interval=interval):
        logger.info(_("开始触发dbha！"))
        sfod.create_run_failover_drill_ticket()
    else:
        # 先打印日志，后续记录到表里
        info = _("Failover drill failed when applying the cluster! root_id: {}".format(sfod.apply_root_id))
        logger.error(info)
        sfod.update_drill_report(info)
        return

    if not cluster_status_polling(sfod.get_immute_domain()[0], max_retry, interval):
        info = _("集群状态没变，dbha切换可能没成功，请检查！")
        logger.info(info)
        sfod.update_drill_report(info)

    logger.info(_("开始禁用集群"))
    sfod.tendbcluster_cluster_disable()
    if not flow_status_polling(sfod.disable_root_id, max_retry=max_retry, interval=interval):
        info = _("集群禁用失败，请检查！")
        logger.info(info)
        sfod.update_drill_report(info)
        return

    logger.info(_("集群禁用单据成功执行！开始下架集群"))
    sfod.tendbcluster_cluster_destroy()
    if not flow_status_polling(sfod.destroy_root_id, max_retry=max_retry, interval=interval):
        info = _("集群下架失败，请检查！")
        logger.info(info)
        sfod.update_drill_report(info)
        return

    logger.info(_("集群下架单据成功执行！开始资源重新导进资源池！"))
    sfod.reimport_ha_resource()
    info = _("容灾演练执行成功！")
    logger.info(info)
    dbha_info, dbha_status = sfod.get_dbha_info()
    sfod.update_drill_report(info, dbha_info, True, dbha_status)
