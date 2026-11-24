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
from unittest.mock import patch

import pytest

from backend.exceptions import AppBaseException
from backend.flow.engine.bamboo.scene.common import failover_drill_flow as mod
from backend.flow.plugins.components.collections.common.check_resolv_conf import ExecuteShellScriptComponent
from backend.flow.plugins.components.collections.common.failover_status_check import FailoverStatusCheckComponent

ROOT_ID = "root"
DRILL_IP = "1.1.1.1"
SERVICE_IPS = ["2.2.2.2", "3.3.3.3"]
V1_IPS = ["1.1.1.9"]
START_PROBE = object()


class RecordingSubBuilder:
    instances = []

    def __init__(self, root_id, data):
        self.acts = []
        self.parallel_sub_flows = []
        RecordingSubBuilder.instances.append(self)

    def add_act(self, act_name, act_component_code, kwargs):
        self.acts.append(("act", act_name, act_component_code, kwargs))

    def add_sub_pipeline(self, sub_flow):
        self.acts.append(("sub", sub_flow))

    def add_parallel_sub_pipeline(self, sub_flow_list):
        self.parallel_sub_flows.append(sub_flow_list)
        self.acts.append(("parallel_sub", sub_flow_list))

    def build_sub_process(self, sub_name):
        return {"sub_name": sub_name, "acts": self.acts}


class RecordingBuilder(RecordingSubBuilder):
    def __init__(self, root_id, data):
        super().__init__(root_id, data)
        self.run_called = False

    def run_pipeline(self, **kwargs):
        self.run_called = True
        return True


def _drill_info(**extra):
    info = {
        "cluster_id": 7,
        "bk_cloud_id": 0,
        "cluster_type": "TwemproxyRedisInstance",
        "types": ["proxy"],
        "proxy": {"ip": DRILL_IP, "logical_city_id": 1},
    }
    info.update(extra)
    return info


@pytest.fixture
def flow():
    RecordingSubBuilder.instances = []
    with patch.object(mod, "SubBuilder", RecordingSubBuilder):
        yield mod.FailoverDrillFlow(root_id=ROOT_ID, data={"bk_biz_id": 3, "drill_infos": []})


def _v1_expected():
    add_cmd = "iptables -I INPUT -s 2.2.2.2 -j DROP"
    clean_cmd = "iptables -D INPUT -s 2.2.2.2 -j DROP"
    return [
        (
            "act",
            "在目标{}添加iptables禁用规则".format(DRILL_IP),
            ExecuteShellScriptComponent.code,
            {"bk_cloud_id": 0, "exec_ip": DRILL_IP, "cluster": {"shell_command": add_cmd}},
        ),
        (
            "act",
            "监测DBHA切换状态",
            FailoverStatusCheckComponent.code,
            {
                "trans_data_dataclass": "FailoverDrillContext",
                "cloud_id": 0,
                "app": "3",
                "ip": DRILL_IP,
                "main_task_id": 0,
                "instance_role": "proxy",
            },
        ),
        (
            "act",
            "清理目标{}的iptables禁用规则".format(DRILL_IP),
            ExecuteShellScriptComponent.code,
            {"bk_cloud_id": 0, "exec_ip": DRILL_IP, "cluster": {"shell_command": clean_cmd}},
        ),
    ]


class TestV1Acts:
    @pytest.mark.parametrize("extra", [{}, {"dbha_version": "v1"}])
    def test_v1_acts_unchanged(self, flow, extra):
        with patch.object(mod.HADBApi, "ha_status", return_value={"data": [{"ip": "2.2.2.2"}]}), patch.object(
            mod, "get_dbha_v2_service_ips"
        ) as v2_ips, patch.object(mod, "probe_start_sub_flow") as start_probe:
            sub = flow._create_sub_pipeline(_drill_info(**extra), "proxy")

        assert sub["acts"] == _v1_expected()
        v2_ips.assert_not_called()
        start_probe.assert_not_called()


class TestV2Acts:
    def test_v2_acts_order(self, flow):
        with patch.object(mod.env, "ENABLE_DBHA_V2", True), patch.object(
            mod, "get_dbha_v2_service_ips", return_value=SERVICE_IPS
        ), patch.object(mod, "probe_start_sub_flow", return_value=START_PROBE) as start_probe, patch.object(
            mod.HADBApi, "ha_status"
        ) as ha_status:
            sub = flow._create_sub_pipeline(_drill_info(dbha_version="v2"), "proxy")

        ha_status.assert_not_called()
        start_probe.assert_called_once_with(root_id=ROOT_ID, data=flow.data, bk_cloud_id=0, ips=[DRILL_IP])

        acts = sub["acts"]
        assert [a[0] for a in acts] == ["act", "act", "act", "sub"]
        trigger, check, clean, probe = acts
        assert trigger[2] == ExecuteShellScriptComponent.code
        assert "account_alias" not in trigger[3]
        assert check[2] == FailoverStatusCheckComponent.code
        assert check[3]["dbha_version"] == "v2"
        assert check[3]["ip"] == DRILL_IP
        assert clean[3]["cluster"]["shell_command"] == (
            "iptables -D INPUT -s 2.2.2.2 -j DROP || true; iptables -D INPUT -s 3.3.3.3 -j DROP || true"
        )
        assert probe == ("sub", START_PROBE)

    def test_v2_trigger_script_blocks_before_stopping_probe(self):
        script = mod.FailoverDrillFlow.get_v2_trigger_script(SERVICE_IPS)

        assert "set -e" in script
        trap_pos = script.index("trap ")
        su_pos = script.index('su - mysql -c "cd /home/mysql/dbha-v2 && ./stop-probe.sh"')
        for ip in SERVICE_IPS:
            assert script.index("iptables -I INPUT -s {} -j DROP".format(ip)) < su_pos
            assert "iptables -D INPUT -s {} -j DROP".format(ip) in script[trap_pos:su_pos]
        assert "ERR" in script[trap_pos:su_pos]

    def test_v2_empty_service_ips_raises_without_acts(self, flow):
        with patch.object(mod.env, "ENABLE_DBHA_V2", True), patch.object(
            mod, "get_dbha_v2_service_ips", return_value=[]
        ), patch.object(mod, "probe_start_sub_flow", return_value=START_PROBE):
            with pytest.raises(AppBaseException):
                flow._create_sub_pipeline(_drill_info(dbha_version="v2"), "proxy")

        assert all(not b.acts for b in RecordingSubBuilder.instances)

    def test_v2_disabled_raises_without_acts(self, flow):
        with patch.object(mod.env, "ENABLE_DBHA_V2", False), patch.object(
            mod, "get_dbha_v2_service_ips", return_value=SERVICE_IPS
        ):
            with pytest.raises(AppBaseException):
                flow._create_sub_pipeline(_drill_info(dbha_version="v2"), "proxy")

        assert all(not b.acts for b in RecordingSubBuilder.instances)

    def test_v2_probe_start_none_raises(self, flow):
        with patch.object(mod.env, "ENABLE_DBHA_V2", True), patch.object(
            mod, "get_dbha_v2_service_ips", return_value=SERVICE_IPS
        ), patch.object(mod, "probe_start_sub_flow", return_value=None):
            with pytest.raises(AppBaseException):
                flow._create_sub_pipeline(_drill_info(dbha_version="v2"), "proxy")

        assert all(not b.acts for b in RecordingSubBuilder.instances)


class TestCombinedActs:
    def test_combined_blocks_v1_and_v2_ips_and_monitors_v2_queue(self, flow):
        with patch.object(mod.env, "ENABLE_DBHA_V2", True), patch.object(
            mod, "get_dbha_v2_service_ips", return_value=SERVICE_IPS
        ), patch.object(mod, "probe_start_sub_flow", return_value=START_PROBE), patch.object(
            mod.HADBApi, "ha_status", return_value={"data": [{"ip": V1_IPS[0]}]}
        ):
            sub = flow._create_sub_pipeline(_drill_info(dbha_version="v1,v2"), "proxy")

        trigger, check, clean, _probe = sub["acts"]
        script = trigger[3]["cluster"]["shell_command"]
        for ip in V1_IPS + SERVICE_IPS:
            assert "iptables -I INPUT -s {} -j DROP".format(ip) in script
            assert "iptables -D INPUT -s {} -j DROP".format(ip) in clean[3]["cluster"]["shell_command"]
        assert check[3]["dbha_version"] == "v2"

    def test_combined_missing_v1_ips_raises_without_acts(self, flow):
        with patch.object(mod.env, "ENABLE_DBHA_V2", True), patch.object(
            mod, "get_dbha_v2_service_ips", return_value=SERVICE_IPS
        ), patch.object(mod, "probe_start_sub_flow", return_value=START_PROBE), patch.object(
            mod.HADBApi, "ha_status", return_value={"data": []}
        ):
            with pytest.raises(AppBaseException):
                flow._create_sub_pipeline(_drill_info(dbha_version="v1,v2"), "proxy")

        assert all(not b.acts for b in RecordingSubBuilder.instances)

    def test_combined_missing_v2_ips_raises_without_acts(self, flow):
        with patch.object(mod.env, "ENABLE_DBHA_V2", True), patch.object(
            mod, "get_dbha_v2_service_ips", return_value=[]
        ), patch.object(mod, "probe_start_sub_flow", return_value=START_PROBE), patch.object(
            mod.HADBApi, "ha_status", return_value={"data": [{"ip": V1_IPS[0]}]}
        ):
            with pytest.raises(AppBaseException):
                flow._create_sub_pipeline(_drill_info(dbha_version="v1,v2"), "proxy")

        assert all(not b.acts for b in RecordingSubBuilder.instances)

    def test_pure_v2_still_skips_v1_ips(self, flow):
        with patch.object(mod.env, "ENABLE_DBHA_V2", True), patch.object(
            mod, "get_dbha_v2_service_ips", return_value=SERVICE_IPS
        ), patch.object(mod, "probe_start_sub_flow", return_value=START_PROBE), patch.object(
            mod.HADBApi, "ha_status"
        ) as ha_status:
            sub = flow._create_sub_pipeline(_drill_info(dbha_version="v2"), "proxy")

        ha_status.assert_not_called()
        script = sub["acts"][0][3]["cluster"]["shell_command"]
        assert V1_IPS[0] not in script
        for ip in SERVICE_IPS:
            assert ip in script


class TestDualRoleParallelAndIsolation:
    def _dual_drill_infos(self, dbha_version="v1"):
        return [
            {
                "main_task_id": "dual-1",
                "cluster_id": 7,
                "bk_cloud_id": 0,
                "cluster_type": "TwemproxyRedisInstance",
                "dbha_version": dbha_version,
                "types": ["proxy"],
                "proxy": {"ip": "1.1.1.1", "logical_city_id": 1},
            },
            {
                "main_task_id": "dual-1",
                "cluster_id": 7,
                "bk_cloud_id": 0,
                "cluster_type": "TwemproxyRedisInstance",
                "dbha_version": dbha_version,
                "types": ["backend"],
                "backend": {"ip": "2.2.2.2", "logical_city_id": 2},
            },
        ]

    def test_multi_drill_infos_run_parallel_and_isolate_v1_ips_by_city(self):
        RecordingSubBuilder.instances = []
        city_hadb_map = {
            (1, "agent"): ["1.1.1.9"],
            (2, "agent"): ["3.3.3.3"],
        }

        def fake_ha_status(params, raw=True):
            q = params["query_args"]
            if q["module"] == "agent":
                return {"data": [{"ip": ip} for ip in city_hadb_map[(q["city_id"], "agent")]]}
            return {"data": [{"ip": "2.2.2.2"}]}

        data = {
            "bk_biz_id": 3,
            "ticket_type": "REDIS_FAILOVER_DRILL",
            "drill_infos": self._dual_drill_infos(dbha_version="v1"),
        }
        with patch.object(mod, "Builder", RecordingBuilder), patch.object(
            mod, "SubBuilder", RecordingSubBuilder
        ), patch.object(mod.HADBApi, "ha_status", side_effect=fake_ha_status), patch.object(
            mod.FailoverDrillFlow, "report_trigger_time"
        ):
            flow_obj = mod.FailoverDrillFlow(root_id=ROOT_ID, data=data)
            flow_obj.failover_drill()

        root_builder = [b for b in RecordingSubBuilder.instances if isinstance(b, RecordingBuilder)][0]
        assert len(root_builder.parallel_sub_flows) == 1
        parallel_branches = root_builder.parallel_sub_flows[0]
        assert len(parallel_branches) == 2

        proxy_acts = parallel_branches[0]["acts"][0][1]["acts"]
        backend_acts = parallel_branches[1]["acts"][0][1]["acts"]
        proxy_add = proxy_acts[0][3]["cluster"]["shell_command"]
        proxy_clean = proxy_acts[2][3]["cluster"]["shell_command"]
        backend_add = backend_acts[0][3]["cluster"]["shell_command"]
        backend_clean = backend_acts[2][3]["cluster"]["shell_command"]

        assert "1.1.1.9" in proxy_add and "3.3.3.3" not in proxy_add
        assert "1.1.1.9" in proxy_clean and "3.3.3.3" not in proxy_clean
        assert "3.3.3.3" in backend_add and "1.1.1.9" not in backend_add
        assert "3.3.3.3" in backend_clean and "1.1.1.9" not in backend_clean

    def test_report_trigger_time_falls_back_to_combined_report(self, request):
        from django.test import TestCase

        from backend.db_meta.enums import ClusterType
        from backend.db_report.models import FailoverDrillReport
        from backend.flow.plugins.components.collections.common.failover_status_check import FailoverStatusCheckService

        old = TestCase.databases
        TestCase.databases = {"default", "report_db"}
        try:
            request.getfixturevalue("db")
            rpt = FailoverDrillReport.objects.create(
                bk_biz_id=3,
                cluster_type=ClusterType.TendisTwemproxyRedisInstance,
                main_task_id="m-dual-trigger",
                instance_type="proxy+backend",
            )
            flow_obj = mod.FailoverDrillFlow(root_id=ROOT_ID, data={"bk_biz_id": 3, "drill_infos": []})
            flow_obj.report_trigger_time("m-dual-trigger", "proxy")
            rpt.refresh_from_db()
            assert rpt.trigger_dbha_time is not None

            FailoverDrillReport.objects.filter(id=rpt.id).update(trigger_dbha_time=None)
            FailoverStatusCheckService().report_trigger_time("m-dual-trigger", "backend")
            rpt.refresh_from_db()
            assert rpt.trigger_dbha_time is not None
        finally:
            TestCase.databases = old

    def test_legacy_mysql_v1_build_dbha_iptables_scripts_clean_not_empty(self):
        from backend.flow.engine.bamboo.scene.mysql.mysql_failover_drill_v1_flow import build_dbha_iptables_scripts

        def fake_ha_status(params, raw=True):
            if params["query_args"]["module"] == "agent":
                return {"data": [{"ip": "1.1.1.9"}]}
            return {"data": [{"ip": "2.2.2.2"}]}

        with patch.object(mod.HADBApi, "ha_status", side_effect=fake_ha_status):
            add_cmd, clean_cmd = build_dbha_iptables_scripts(bk_cloud_id=0, logical_city_id=1, cluster_type="tendbha")

        assert "iptables -I INPUT -s 1.1.1.9 -j DROP" in add_cmd
        assert "iptables -I INPUT -s 2.2.2.2 -j DROP" in add_cmd
        assert "iptables -D INPUT -s 1.1.1.9 -j DROP || true" in clean_cmd
        assert "iptables -D INPUT -s 2.2.2.2 -j DROP || true" in clean_cmd
