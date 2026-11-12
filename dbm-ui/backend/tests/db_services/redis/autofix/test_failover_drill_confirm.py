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
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_periodic_task.models import FailoverDrillConfig
from backend.db_services.redis.autofix import bill

V2_DOMAIN = "cache.my-drill.test.db"
CLUSTER_TYPE = ClusterType.TendisTwemproxyRedisInstance.value

pytestmark = pytest.mark.django_db


def _config(**extra):
    data = {"labels": [], "cluster_type": CLUSTER_TYPE, "version": "v2", "switch_flag": True}
    data.update(extra)
    return FailoverDrillConfig.objects.create(**data)


def _need_manual_confirm(immute_domain):
    cluster = MagicMock(immute_domain=immute_domain, bk_cloud_id=0, bk_biz_id=3)
    proxies = [{"ip": "1.1.1.1", "spec_id": 1, "instance_type": InstanceRole.REDIS_PROXY.value}]
    with patch.object(bill.Ticket, "create_ticket") as create_ticket, patch.object(
        bill.DBAdministrator.objects, "get", return_value=MagicMock(users=["dba"])
    ), patch.object(bill, "get_ticket_heplers", return_value=[]), patch.object(bill, "send_msg_2_qywx"):
        bill.create_ticket(cluster, [1], proxies, [], InstanceRole.REDIS_PROXY.value)
    return create_ticket.call_args.kwargs["details"]["infos"][0]["need_manual_confirm"]


@pytest.mark.parametrize(
    "domain, configs, expected",
    [
        ("cache.failover-drill-sz.test.db", [], False),
        (V2_DOMAIN, [{"cluster_domain": V2_DOMAIN}], False),
        (V2_DOMAIN, [{"cluster_domain": V2_DOMAIN, "version": "v1,v2"}], False),
        (V2_DOMAIN, [{"cluster_domain": V2_DOMAIN, "switch_flag": False}], True),
        (V2_DOMAIN, [{"cluster_domain": V2_DOMAIN, "version": "v1"}], True),
        ("cache.normal.test.db", [{"cluster_domain": V2_DOMAIN}], True),
    ],
    ids=[
        "v1-prefix",
        "enabled-v2-domain",
        "enabled-combined-domain",
        "disabled-v2-domain",
        "v1-row-domain",
        "normal-cluster",
    ],
)
def test_need_manual_confirm(domain, configs, expected):
    for extra in configs:
        _config(**extra)

    assert bill.is_failover_drill_cluster(domain) is not expected
    assert _need_manual_confirm(domain) is expected
