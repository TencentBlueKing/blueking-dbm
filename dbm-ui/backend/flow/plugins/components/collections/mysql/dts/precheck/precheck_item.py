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

import json
import logging

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

import backend.flow.utils.mysql.dts.precheck.items  # noqa: F401
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.dts.precheck.base import (
    CheckContext,
    CheckItem,
    CheckLevel,
    CheckResult,
    get_item,
    run_item,
)
from backend.flow.utils.mysql.dts.precheck.collector import InstanceCollector, PrecheckCollectError
from backend.flow.utils.mysql.dts.precheck.endpoint import Side, resolve_endpoint
from backend.flow.utils.mysql.dts.precheck.scope import SyncScope
from backend.flow.utils.mysql.dts.precheck.summary import SKIPPED_NO_FLOW, collect_error_result, write_precheck_summary

logger = logging.getLogger("root")


def _source_address(kwargs: dict, cluster: Cluster) -> str:
    if kwargs.get("source_host"):
        return kwargs["source_host"]
    instance_id = kwargs.get("source_instance_id")
    if not instance_id:
        return ""
    instance = StorageInstance.objects.select_related("machine").filter(id=instance_id, cluster=cluster).first()
    if instance is None:
        raise PrecheckCollectError(_("源实例 {} 不属于源集群 {} 或不存在").format(instance_id, cluster.id))
    return instance.ip_port


def build_context(kwargs: dict) -> CheckContext:
    try:
        source_cluster = Cluster.objects.get(id=kwargs["source_cluster_id"])
        target_cluster = Cluster.objects.get(id=kwargs["target_cluster_id"])
    except Cluster.DoesNotExist as exc:
        raise PrecheckCollectError(_("集群不存在: {}").format(exc)) from exc

    source = InstanceCollector(
        resolve_endpoint(
            source_cluster,
            Side.SOURCE,
            address=_source_address(kwargs, source_cluster),
        )
    )
    target = InstanceCollector(
        resolve_endpoint(
            target_cluster,
            Side.TARGET,
            address=kwargs.get("target_host") or kwargs.get("target_spider") or "",
        )
    )
    scope = dict(kwargs.get("precheck_scope") or kwargs.get("sync_scope") or {})
    if kwargs.get("source_tables"):
        scope["source_tables"] = kwargs["source_tables"]
    return CheckContext(
        source=source,
        target=target,
        scope=SyncScope(**scope),
    )


class MysqlDtsPrecheckItemService(BaseService):
    """跑一个已登记的检查项，并把这个大项的结论写进执行摘要。

    摘要一行是一对源/目标。新检查项只要 @register、放进检查阶段，并返回 CheckResult。
    不用改摘要的列定义。
    """

    def _record_summary(self, item: CheckItem, results: list[CheckResult], kwargs: dict) -> None:
        root_id = self.runtime_attrs.get("root_pipeline_id")
        extra = {}
        if kwargs.get("pair_key"):
            extra["pair_key"] = kwargs["pair_key"]
        if kwargs.get("scope_label"):
            extra["scope_label"] = kwargs["scope_label"]
        outcome = write_precheck_summary(
            root_id,
            item,
            results,
            kwargs.get("source_cluster_domain") or "",
            kwargs.get("target_cluster_domain") or "",
            kwargs.get("enabled_codes"),
            **extra,
        )
        if outcome == SKIPPED_NO_FLOW:
            self.log_info(_("当前流程[{}]未关联单据Flow记录，跳过写入执行摘要").format(root_id))

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        item = get_item(kwargs["item_code"])
        try:
            context = build_context(kwargs)
        except PrecheckCollectError as exc:
            message = _("DTS预检查 {} 采集失败: {}").format(item.code, exc)
            logger.error(message)
            self.log_error(message)
            self._record_summary(item, [collect_error_result(item, str(exc))], kwargs)
            return False

        logger.info(
            _("DTS预检查开始 %s(%s): 源 %s(%s) %s -> 目标 %s(%s) %s"),
            item.name,
            item.code,
            kwargs.get("source_cluster_domain"),
            context.source.endpoint.cluster_id,
            context.source.endpoint.address,
            kwargs.get("target_cluster_domain"),
            context.target.endpoint.cluster_id,
            context.target.endpoint.address,
        )
        try:
            results = run_item(item, context)
        except PrecheckCollectError as exc:
            message = _("DTS预检查 {} 采集失败: {}").format(item.code, exc)
            logger.error(message)
            self.log_error(message)
            self._record_summary(item, [collect_error_result(item, str(exc))], kwargs)
            return False

        has_failure = False
        for result in results:
            details = json.dumps(result.details, ensure_ascii=False, default=str)
            message = _("DTS预检查 {} {}: {}; details={}").format(item.code, result.code, result.message, details)
            if result.ok:
                logger.info(message)
                self.log_info(message)
            elif result.level == CheckLevel.WARN:
                logger.warning(message)
                self.log_warning(message)
            else:
                has_failure = True
                logger.error(message)
                self.log_error(message)
        self._record_summary(item, results, kwargs)
        conclusion = _("DTS预检查结束 {}({})").format(item.name, _("未通过") if has_failure else _("通过"))
        if has_failure:
            logger.error(conclusion)
            self.log_error(conclusion)
            return False
        logger.info(conclusion)
        self.log_info(conclusion)
        return True


class MysqlDtsPrecheckItemComponent(Component):
    name = __name__
    code = "mysql_dts_precheck_item"
    bound_service = MysqlDtsPrecheckItemService
