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
from typing import List, Set, Tuple, Type

from django.db.models import Model
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.db_meta.enums import InstanceStatus
from backend.db_meta.models import ProxyInstance, StorageInstance
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("json")

_ALLOWED_STATUS = {
    InstanceStatus.UNAVAILABLE.value,
    InstanceStatus.RUNNING.value,
    InstanceStatus.UPGRADING.value,
}
_INSTANCE_KIND_STORAGE = "storage"
_INSTANCE_KIND_PROXY = "proxy"
_INSTANCE_KIND_AUTO = "auto"


class ChangeInstanceStatusByAddrsService(BaseService):
    """
    按 ip:port / instance_id 更新 StorageInstance / ProxyInstance.status。

    kwargs:
    {
      "addrs": ["ip:port", ...],           # 与 instance_ids 二选一或同时提供
      "instance_ids": [1, 2, ...],
      "status": "unavailable" | "running" | "upgrading",
      "instance_kind": "storage" | "proxy" | "auto",  # auto: 先 storage 再 proxy
    }
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        status = kwargs.get("status")
        instance_kind = (kwargs.get("instance_kind") or _INSTANCE_KIND_AUTO).lower()
        addrs = kwargs.get("addrs") or []
        instance_ids = kwargs.get("instance_ids") or []

        if status not in _ALLOWED_STATUS:
            self.log_error("invalid status:{}, allowed:{}".format(status, sorted(_ALLOWED_STATUS)))
            return False
        if instance_kind not in {_INSTANCE_KIND_STORAGE, _INSTANCE_KIND_PROXY, _INSTANCE_KIND_AUTO}:
            self.log_error("invalid instance_kind:{}".format(instance_kind))
            return False
        if not addrs and not instance_ids:
            self.log_error("addrs or instance_ids required")
            return False

        try:
            updated, leftover_addrs, leftover_ids = self._update_instances(
                addrs=addrs, instance_ids=instance_ids, status=status, instance_kind=instance_kind
            )
        except Exception as e:
            logger.error(
                "change instance status by addrs/ids fail, status:{}, error:{}".format(status, e),
                exc_info=True,
            )
            self.log_error("change instance status fail: {}".format(e))
            return False

        if leftover_addrs or leftover_ids:
            self.log_error(
                "unmatched addrs:{}, instance_ids:{}, kind:{}".format(leftover_addrs, leftover_ids, instance_kind)
            )
            return False

        if updated == 0:
            self.log_error(
                "no instance updated, addrs:{}, instance_ids:{}, kind:{}".format(addrs, instance_ids, instance_kind)
            )
            return False

        self.log_info(
            "change instance status to {} successfully, updated={}, addrs={}, instance_ids={}, kind={}".format(
                status, updated, addrs, instance_ids, instance_kind
            )
        )
        return True

    def _update_instances(
        self, addrs: List[str], instance_ids: List[int], status: str, instance_kind: str
    ) -> Tuple[int, Set[str], Set[int]]:
        models = self._models_for_kind(instance_kind)
        updated = 0
        remaining_addrs = set(addrs) if addrs else set()
        remaining_ids = set(int(i) for i in instance_ids) if instance_ids else set()

        for model in models:
            if remaining_addrs:
                matched = self._matched_addrs(model, remaining_addrs)
                if matched:
                    count = model.find_insts_by_addresses(list(matched)).update(status=status)
                    updated += count
                    remaining_addrs -= matched
            if remaining_ids:
                qs = model.objects.filter(id__in=list(remaining_ids))
                matched_ids = set(qs.values_list("id", flat=True))
                if matched_ids:
                    count = qs.update(status=status)
                    updated += count
                    remaining_ids -= matched_ids

        return updated, remaining_addrs, remaining_ids

    @staticmethod
    def _models_for_kind(instance_kind: str) -> List[Type[Model]]:
        if instance_kind == _INSTANCE_KIND_STORAGE:
            return [StorageInstance]
        if instance_kind == _INSTANCE_KIND_PROXY:
            return [ProxyInstance]
        return [StorageInstance, ProxyInstance]

    @staticmethod
    def _matched_addrs(model: Type[Model], addrs: Set[str]) -> Set[str]:
        qs = model.find_insts_by_addresses(list(addrs))
        if qs is None:
            return set()
        matched = set()
        for row in qs.values("machine__ip", "port"):
            matched.add("{}:{}".format(row["machine__ip"], row["port"]))
        return matched

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class ChangeInstanceStatusByAddrsComponent(Component):
    name = __name__
    code = "change_instance_status_by_addrs"
    bound_service = ChangeInstanceStatusByAddrsService
