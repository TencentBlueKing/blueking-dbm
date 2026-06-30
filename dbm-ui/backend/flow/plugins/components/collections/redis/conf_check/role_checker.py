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
from typing import Dict, List, Optional, Tuple

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_report.enums import ReportStateType
from backend.flow.utils.redis.redis_util import decode_info_cmd

from .base import BaseConfChecker, CheckTarget, ConfCheckResult
from .registry import redis_conf_checker

# meta instance_role -> redis INFO REPLICATION role
ROLE_NORMALIZE = {"redis_master": "master", "redis_slave": "slave"}


@redis_conf_checker
class RoleChecker(BaseConfChecker):
    """
    Verify each storage instance's actual replication role (live `INFO REPLICATION`)
    matches the role recorded in db_meta. Live state is read via DRS, so this
    checker delivers no on-host script.
    """

    name = "role"
    cluster_types = [
        ClusterType.TendisPredixyRedisCluster.value,
        ClusterType.TendisPredixyTendisplusCluster.value,
        ClusterType.TendisTwemproxyRedisInstance.value,
        ClusterType.TwemproxyTendisSSDInstance.value,
        ClusterType.TendisRedisInstance.value,
    ]

    def collect_targets(self, cluster) -> List[CheckTarget]:
        targets = []
        if "storageinstance_set" in getattr(cluster, "_prefetched_objects_cache", {}):
            storages = cluster.storageinstance_set.all()
        else:
            storages = cluster.storageinstance_set.select_related("machine").all()
        for inst in storages:
            targets.append(
                CheckTarget(
                    cluster_id=cluster.id,
                    bk_cloud_id=cluster.bk_cloud_id,
                    ip=inst.machine.ip,
                    port=inst.port,
                    extra={"meta_role": inst.instance_role},
                )
            )
        return targets

    def drs_request(self, target: CheckTarget) -> Optional[Tuple[str, str]]:
        return "INFO REPLICATION", "redis_password"

    def evaluate(
        self,
        target: CheckTarget,
        drs_result: Optional[str],
        host_block: Optional[Dict],
        checker_config: Optional[Dict] = None,
        drs_error: Optional[str] = None,
    ) -> List[ConfCheckResult]:
        meta_role = target.extra.get("meta_role", "")
        expected = ROLE_NORMALIZE.get(meta_role, meta_role)

        if not drs_result:
            reason = drs_error or "drs_no_result"
            return [
                ConfCheckResult(
                    ip=target.ip,
                    port=target.port,
                    state=ReportStateType.ABNORMAL.value,
                    msg=_("角色检查失败: 无法执行 INFO REPLICATION (meta_role={}, 原因={})").format(meta_role, reason),
                )
            ]

        actual = decode_info_cmd(drs_result).get("role", "")
        if actual and actual == expected:
            state = ReportStateType.NORMAL.value
            msg = _("角色一致: meta={}, actual={}").format(meta_role, actual)
        else:
            state = ReportStateType.ABNORMAL.value
            msg = _("角色不匹配: meta={}, actual={}").format(meta_role, actual or "unknown")

        return [ConfCheckResult(ip=target.ip, port=target.port, state=state, msg=msg)]
