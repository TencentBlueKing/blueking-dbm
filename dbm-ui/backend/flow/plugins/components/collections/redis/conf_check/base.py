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
import abc
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class CheckTarget:
    """A single instance to be checked by a checker."""

    cluster_id: int
    bk_cloud_id: int
    ip: str
    port: int
    # checker-specific context, e.g. {"meta_role": "redis_slave"}
    extra: Dict = field(default_factory=dict)

    @property
    def address(self) -> str:
        return "{}:{}".format(self.ip, self.port)


@dataclass
class ConfCheckResult:
    """
    One report row produced by a checker for a target.

    All conf-check findings share a single report subtype (owned by the report
    service), so a checker only reports the instance, its state and a detail msg.
    """

    ip: str
    port: int
    state: str  # ReportStateType value
    msg: str


class BaseConfChecker(abc.ABC):
    """
    Pluggable config checker.

    The conf-check engine drives every registered checker through the same
    lifecycle for a batch of clusters:

    1. ``collect_targets(cluster)`` -> the instances this checker inspects.
    2. ``host_script_snippet(targets_on_host)`` -> optional bash run on the host
       (only needed to read on-disk config; all live state comes from DRS). The
       collect service concatenates every checker's snippet for a host into ONE
       script and delivers a single job per host.
    3. ``drs_request(target)`` -> optional ``(command, password_key)`` describing
       the live-state query issued via ``DRSApi.redis_rpc``.
    4. ``evaluate(target, drs_result, host_block)`` -> report rows.

    Adding a new check = subclass this and decorate with ``@redis_conf_checker``.
    """

    # Unique, stable identifier used in the tagged <CONFCHK checker="..."> output.
    name: str = ""
    # Cluster types this checker applies to (ClusterType values).
    cluster_types: List[str] = []
    # Whether collect phase needs to run host_script_snippet for this checker.
    requires_host_script: bool = False

    def applies_to(self, cluster_type: str) -> bool:
        return cluster_type in self.cluster_types

    @abc.abstractmethod
    def collect_targets(self, cluster) -> List[CheckTarget]:
        """Return the instances this checker should inspect for the given cluster."""
        raise NotImplementedError

    def host_script_snippet(self, targets_on_host: List[CheckTarget]) -> Optional[str]:
        """
        Return a self-contained bash snippet for this checker's on-host work for
        the targets that live on a single host, or None for DRS-only checkers.

        The snippet must print tagged blocks understood by the report service:
            <CONFCHK checker="<name>" port="<port>">{json}</CONFCHK>
        """
        return None

    def drs_request(self, target: CheckTarget) -> Optional[Tuple[str, str]]:
        """
        Return ``(command, password_key)`` for the live-state DRS query, or None.

        ``password_key`` indexes the dict returned by
        ``PayloadHandler.redis_get_password_by_cluster_id`` (e.g. "redis_password",
        "redis_proxy_password").
        """
        return None

    @abc.abstractmethod
    def evaluate(
        self, target: CheckTarget, drs_result: Optional[str], host_block: Optional[Dict]
    ) -> List[ConfCheckResult]:
        """
        Compare live state (drs_result) and/or on-host config (host_block) against
        the expected state and return report rows. ``drs_result`` is None when the
        DRS query failed; ``host_block`` is None when no on-host data was collected.
        """
        raise NotImplementedError
