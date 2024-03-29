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
import datetime
import glob
import json
import logging
import os

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from backend import env
from backend.bk_web.constants import LEN_MIDDLE, LEN_NORMAL
from backend.bk_web.models import AuditedModel
from backend.components import BKMonitorV3Api
from backend.configuration.constants import PLAT_BIZ_ID, DBType

__all__ = [
    "CollectTemplate",
    "CollectInstance",
]

from backend.db_meta.models import AppMonitorTopo
from backend.db_monitor.constants import TPLS_COLLECT_DIR

logger = logging.getLogger("root")


class CollectTemplateBase(AuditedModel):
    """采集策略模板"""

    bk_biz_id = models.IntegerField(help_text=_("业务ID, 0代表全业务"), default=PLAT_BIZ_ID)
    plugin_id = models.CharField(verbose_name=_("插件ID"), max_length=LEN_MIDDLE)
    name = models.CharField(verbose_name=_("策略名称，全局唯一"), max_length=LEN_MIDDLE, default="")
    db_type = models.CharField(
        _("DB类型"), choices=DBType.get_choices(), max_length=LEN_NORMAL, default=DBType.MySQL.value
    )
    machine_types = models.JSONField(verbose_name=_("绑定machine"), default=list)
    details = models.JSONField(verbose_name=_("详情"), default=dict)

    # 支持版本管理
    version = models.IntegerField(verbose_name=_("版本"), default=0)

    class Meta:
        abstract = True
        verbose_name = _("采集策略模板")


class CollectTemplate(CollectTemplateBase):
    class Meta:
        verbose_name = _("采集策略模板")


class CollectInstance(CollectTemplateBase):
    """采集策略实例"""

    template_id = models.IntegerField(help_text=_("监控插件模板ID"), default=0)
    collect_id = models.IntegerField(help_text=_("监控采集策略ID"))

    sync_at = models.DateTimeField(_("最近一次的同步时间"), null=True)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        super().save(force_insert, force_update, using)

    @staticmethod
    def sync_collect_strategy(bk_biz_id: int = env.DBA_APP_BK_BIZ_ID, db_type: str = None, force=False):
        """同步监控采集项"""
        now = datetime.datetime.now(timezone.utc)
        updated_collectors = 0

        logger.info("[init_collect_strategy] start sync bkmonitor collector start: %s", now)

        # 未来考虑将模板放到db管理
        collect_tpls = os.path.join(TPLS_COLLECT_DIR, "*.json")
        for collect_tpl in glob.glob(collect_tpls):
            with open(collect_tpl, "r") as f:
                template_dict = json.loads(f.read())
                template_dict.pop("export_at", None)
                template = CollectTemplate(**template_dict)

            collect_params = template.details

            # 如果指定了 db_type，则忽略其他db类型的采集模块
            if db_type is not None and template.db_type != db_type:
                continue

            try:
                try:
                    collect_instance = CollectInstance.objects.get(
                        bk_biz_id=template.bk_biz_id,
                        db_type=template.db_type,
                        plugin_id=template.plugin_id,
                        name=template.name,
                        machine_types=template.machine_types,
                    )
                except CollectInstance.DoesNotExist:
                    # 为了能够重复执行，这里考虑下CollectInstance被清空的情况
                    res = BKMonitorV3Api.query_collect_config(
                        {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "search": {"fuzzy": collect_params["name"]}},
                        use_admin=True,
                    )

                    # 业务下存在该策略
                    collect_config_list = res["config_list"]
                    if res["total"] == 1:
                        collect_config = collect_config_list[0]
                        collect_params["id"] = collect_config["id"]
                        logger.warning("[init_collect_strategy] sync bkmonitor collector: %s " % template.db_type)
                    else:
                        logger.warning("[init_collect_strategy] create bkmonitor collector: %s " % template.db_type)
                else:
                    collect_params["id"] = collect_instance.collect_id
                    # 如果版本相同，说明采集模板没有更新，则跳过
                    # 强制执行除外（采集对象有变更时，需要强制执行）
                    if template.version <= collect_instance.version and not force:
                        logger.warning("[init_collect_strategy] skip update bkmonitor collector: %s " % template.name)
                        continue

                logger.info("[init_collect_strategy] update bkmonitor collector: %s " % template.name)
                collect_params.update(
                    bk_biz_id=bk_biz_id,
                    plugin_id=template.plugin_id,
                    target_nodes=[
                        {"bk_inst_id": bk_set_id, "bk_obj_id": "set", "bk_biz_id": bk_biz_id}
                        for bk_set_id, bk_biz_id in AppMonitorTopo.get_set_by_plugin_id(
                            plugin_id=template.plugin_id,
                            machine_types=template.machine_types,
                        )
                    ],
                )
                res = BKMonitorV3Api.save_collect_config(collect_params, use_admin=True)

                # 实例化Rule
                obj, _ = CollectInstance.objects.update_or_create(
                    defaults={"details": collect_params, "collect_id": res["id"], "version": template.version},
                    bk_biz_id=template.bk_biz_id,
                    db_type=template.db_type,
                    plugin_id=template.plugin_id,
                    name=template.name,
                    machine_types=template.machine_types,
                )

                updated_collectors += 1
            except Exception as e:  # pylint: disable=wildcard-import
                logger.error("[init_collect_strategy] sync bkmonitor collector: %s (%s)", template.db_type, e)

        logger.info(
            "[init_collect_strategy] finish sync bkmonitor collector end: %s, update_cnt: %s",
            datetime.datetime.now(timezone.utc) - now,
            updated_collectors,
        )

    class Meta:
        verbose_name = _("采集策略实例")
