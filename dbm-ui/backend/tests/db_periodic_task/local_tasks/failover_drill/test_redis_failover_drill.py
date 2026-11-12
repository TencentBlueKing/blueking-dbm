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
import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase

from backend.db_meta.enums import ClusterStatus, ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.constants import (
    canonical_failover_drill_version,
    failover_drill_has_v2,
    failover_drill_queue_version,
    parse_failover_drill_versions,
)
from backend.db_periodic_task.models import FailoverDrillConfig
from backend.db_report.enums import ReportStateType
from backend.db_report.models import FailoverDrillReport
from backend.db_report.views.redis.redis_failover_drill_view import RedisFailoverDrillSerializer
from backend.db_services.redis.autofix.enums import DBHASwitchResult
from backend.flow.utils import failover_drill_dbha

BIZ_ID = 3
CLOUD_ID = 0
DRILL_IP = "1.1.1.1"
CITY_MAP = {"深圳": "sz", "上海": "sh"}
V2_DOMAIN = "cache.my-drill.test.db"

_PKG = "backend.db_periodic_task.local_tasks"


@pytest.fixture(scope="module", autouse=True)
def drill_modules(django_db_setup, django_db_blocker):
    global drill_mod, unit_mod, task_mod, utils_mod, mysql_unit_mod, RedisFailoverDrill, DrillTarget, build_drill_targets
    with django_db_blocker.unblock():
        drill_mod = importlib.import_module(f"{_PKG}.redis_failover_drill.failover_drill")
        unit_mod = importlib.import_module(f"{_PKG}.redis_failover_drill.failover_drill_unit")
        task_mod = importlib.import_module(f"{_PKG}.redis_failover_drill.task")
        utils_mod = importlib.import_module(f"{_PKG}.redis_failover_drill.utils")
        mysql_unit_mod = importlib.import_module(f"{_PKG}.mysql_failover_drill.failover_drill_unit")
    RedisFailoverDrill = drill_mod.RedisFailoverDrill
    DrillTarget = drill_mod.DrillTarget
    build_drill_targets = drill_mod.build_drill_targets


@pytest.fixture
def multi_db(request):
    """FailoverDrillReport 位于 report_db，pytest-django 3.x 只能通过 TestCase.databases 开启多库"""
    old = TestCase.databases
    TestCase.databases = {"default", "report_db"}
    try:
        request.getfixturevalue("db")
        yield
    finally:
        TestCase.databases = old


class TaskStatus:
    NO_CLUSTER = "no drill cluster"
    NO_CLUSTER_DOMAIN = "no drill cluster domain configured"
    DBHA_QUERY_FAILED = "dbha switch queue query failed"
    SWITCH_FAILED = "switch failed"
    SWITCHED_NO_AUTOFIX = "switched but autofix not generated"
    SWITCHED_AUTOFIX_ERROR = "switched but autofix failed"
    NO_DBHA_V2_SERVICE_IP = "dbha-v2 service ip unavailable"
    SUCCESS = "succeeded"


def _conf(**extra):
    conf = {
        "bk_biz_id": BIZ_ID,
        "bk_cloud_id": CLOUD_ID,
        "labels": [],
        "city_map": CITY_MAP,
        "max_retry": 2,
        "interval": 1,
        "target_type": "proxy",
        "version": "v1",
        "cluster_domain": "",
    }
    conf.update(extra)
    return conf


def _drill(version="v1", immute_domain="cache.failover-drill-sz.test.db", city="深圳"):
    with patch.object(RedisFailoverDrill, "init_report"):
        return RedisFailoverDrill(
            city=city,
            labels=[],
            bk_biz_id=BIZ_ID,
            bk_cloud_id=CLOUD_ID,
            city_map=CITY_MAP,
            instance_type="proxy",
            version=version,
            immute_domain=immute_domain,
        )


class TestModelDefaults:
    @pytest.mark.usefixtures("multi_db")
    def test_config_and_report_default_to_v1(self):
        conf = FailoverDrillConfig.objects.create(labels=[], cluster_type=ClusterType.TendisTwemproxyRedisInstance)
        rpt = FailoverDrillReport.objects.create(
            bk_biz_id=BIZ_ID, cluster_type=ClusterType.TendisTwemproxyRedisInstance, main_task_id="m1"
        )

        conf.refresh_from_db()
        rpt.refresh_from_db()
        assert conf.version == "v1"
        assert conf.cluster_domain == ""
        assert rpt.version == "v1"
        assert RedisFailoverDrillSerializer(rpt).data["version"] == "v1"

    @pytest.mark.usefixtures("multi_db")
    def test_config_and_report_accept_combined_version(self):
        conf = FailoverDrillConfig.objects.create(
            labels=[], cluster_type=ClusterType.TendisTwemproxyRedisInstance, version="v1,v2"
        )
        rpt = FailoverDrillReport.objects.create(
            bk_biz_id=BIZ_ID,
            cluster_type=ClusterType.TendisTwemproxyRedisInstance,
            main_task_id="m-combo",
            version="v1,v2",
        )
        conf.refresh_from_db()
        rpt.refresh_from_db()
        assert conf.version == "v1,v2"
        assert rpt.version == "v1,v2"
        assert RedisFailoverDrillSerializer(rpt).data["version"] == "v1,v2"


class TestParseFailoverDrillVersions:
    @pytest.mark.parametrize(
        "raw, parsed, canonical, has_v2, queue",
        [
            ("v1", {"v1"}, "v1", False, "v1"),
            ("v2", {"v2"}, "v2", True, "v2"),
            ("v1,v2", {"v1", "v2"}, "v1,v2", True, "v2"),
            ("v2,v1", {"v1", "v2"}, "v1,v2", True, "v2"),
            (" v1 , v2 ", {"v1", "v2"}, "v1,v2", True, "v2"),
            (None, {"v1"}, "v1", False, "v1"),
            ("", {"v1"}, "v1", False, "v1"),
        ],
    )
    def test_parse_canonical_queue(self, raw, parsed, canonical, has_v2, queue):
        assert parse_failover_drill_versions(raw) == frozenset(parsed)
        assert canonical_failover_drill_version(raw) == canonical
        assert failover_drill_has_v2(raw) is has_v2
        assert failover_drill_queue_version(raw) == queue


class TestGetDbhaSwitchData:
    @pytest.mark.parametrize(
        "version, client_attr",
        [("v1", "HADBApi"), ("v2", "HADBApiV2"), ("v1,v2", "HADBApiV2"), ("v2,v1", "HADBApiV2")],
    )
    def test_select_client_by_instance_version(self, version, client_attr):
        rfod = _drill(version=version)
        resp = {"code": 0, "msg" if client_attr == "HADBApi" else "message": "ok", "data": []}
        other = "HADBApiV2" if client_attr == "HADBApi" else "HADBApi"
        with patch.object(
            getattr(failover_drill_dbha, client_attr), "switch_queue", return_value=resp
        ) as used, patch.object(getattr(failover_drill_dbha, other), "switch_queue") as unused:
            assert rfod.get_dbha_switch_data() == {"code": 0, "msg": "ok", "data": []}

        used.assert_called_once()
        unused.assert_not_called()


class TestGetDbhaInfo:
    def test_duplicate_records_prefer_success(self):
        rfod = _drill(version="v2")
        rfod.target_instances = {f"{DRILL_IP}:30000"}
        rfod.failover_drill_info = {"drill_infos": [{"proxy": {"ip": DRILL_IP, "logical_city_id": 1}}]}
        failed = {"ip": DRILL_IP, "slave_ip": "", "port": 30000, "status": "failed"}
        success = {"ip": DRILL_IP, "slave_ip": "", "port": 30000, "status": "success"}
        with patch.object(
            rfod, "get_dbha_switch_data", return_value={"code": 0, "msg": "", "data": [failed, success]}
        ):
            dbha_infos, queue_status = rfod.get_dbha_info()

        assert queue_status is True
        assert dbha_infos["error"] == ""
        assert dbha_infos[f"{DRILL_IP}:30000"] is success

    def test_success_not_overwritten_by_later_failure(self):
        rfod = _drill()
        rfod.target_instances = {f"{DRILL_IP}:30000"}
        rfod.failover_drill_info = {"drill_infos": [{"proxy": {"ip": DRILL_IP, "logical_city_id": 1}}]}
        success = {"ip": DRILL_IP, "slave_ip": "", "port": 30000, "status": "success"}
        failed = {"ip": DRILL_IP, "slave_ip": "", "port": 30000, "status": "failed"}
        with patch.object(
            rfod, "get_dbha_switch_data", return_value={"code": 0, "msg": "", "data": [success, failed]}
        ):
            dbha_infos, _ = rfod.get_dbha_info()

        assert dbha_infos[f"{DRILL_IP}:30000"] is success


class TestBuildDrillTargets:
    @pytest.fixture(autouse=True)
    def app_cache(self):
        with patch.object(drill_mod.AppCache.objects, "get", return_value=SimpleNamespace(db_app_abbr="test")):
            yield

    def test_v1_targets_per_city(self):
        assert build_drill_targets(_conf()) == [
            DrillTarget("深圳", "cache.failover-drill-sz.test.db"),
            DrillTarget("上海", "cache.failover-drill-sh.test.db"),
        ]

    def test_v1_ignores_cluster_domain(self):
        assert build_drill_targets(_conf(cluster_domain=V2_DOMAIN)) == build_drill_targets(_conf())

    def test_v2_with_domain_single_target(self):
        assert build_drill_targets(_conf(version="v2", cluster_domain=V2_DOMAIN)) == [DrillTarget("", V2_DOMAIN)]

    def test_v2_without_domain_single_empty_target(self):
        assert build_drill_targets(_conf(version="v2")) == [DrillTarget("", "")]

    def test_v2_ignores_city_map_and_app_cache(self):
        with patch.object(drill_mod.AppCache.objects, "get", side_effect=drill_mod.AppCache.DoesNotExist) as get:
            targets = build_drill_targets(_conf(version="v2", city_map={}, cluster_domain=V2_DOMAIN))

        assert targets == [DrillTarget("", V2_DOMAIN)]
        get.assert_not_called()

    def test_v2_empty_domain_no_v1_fallback(self):
        assert _drill(version="v2", immute_domain="").get_immute_domain() == ""

    def test_combined_version_uses_cluster_domain(self):
        assert build_drill_targets(_conf(version="v2,v1", cluster_domain=V2_DOMAIN, city_map={"深圳": "sz"})) == [
            DrillTarget("", V2_DOMAIN)
        ]


class TestRedisFailoverDrillReport:
    @pytest.mark.usefixtures("multi_db")
    def test_v2_report_version_domain_city_and_ticket_details(self):
        with patch.object(RedisFailoverDrill, "resolve_city_by_ip", return_value="深圳"):
            rfod = RedisFailoverDrill(
                city="",
                labels=[],
                bk_biz_id=BIZ_ID,
                bk_cloud_id=CLOUD_ID,
                city_map=CITY_MAP,
                instance_type="proxy",
                version="v2",
                immute_domain=V2_DOMAIN,
            )
            rpt = FailoverDrillReport.objects.get(main_task_id=rfod.main_task_id)
            assert (rpt.version, rpt.cluster_domain, rpt.city) == ("v2", V2_DOMAIN, "-")

            cluster = SimpleNamespace(
                id=7, bk_cloud_id=CLOUD_ID, cluster_type=ClusterType.TendisTwemproxyRedisInstance
            )
            with patch.object(drill_mod.Cluster.objects, "get", return_value=cluster), patch.object(
                rfod, "get_instance_info", return_value={"ip": DRILL_IP, "logical_city_id": 1}
            ), patch.object(rfod, "get_drill_instances", return_value=set()), patch.object(
                drill_mod.Ticket, "create_ticket"
            ) as create_ticket:
                rfod.get_failover_drill_params()
                rfod.create_run_failover_drill_ticket()

        rpt.refresh_from_db()
        assert rpt.city == "深圳"
        assert rfod.city == "深圳"
        details = create_ticket.call_args.kwargs["details"]
        assert details["drill_infos"][0]["dbha_version"] == "v2"

    @pytest.mark.usefixtures("multi_db")
    def test_combined_version_report_and_ticket_keep_canonical(self):
        with patch.object(RedisFailoverDrill, "resolve_city_by_ip", return_value="深圳"):
            rfod = RedisFailoverDrill(
                city="",
                labels=[],
                bk_biz_id=BIZ_ID,
                bk_cloud_id=CLOUD_ID,
                city_map=CITY_MAP,
                instance_type="proxy",
                version="v2,v1",
                immute_domain=V2_DOMAIN,
            )
            rpt = FailoverDrillReport.objects.get(main_task_id=rfod.main_task_id)
            assert rpt.version == "v1,v2"
            cluster = SimpleNamespace(
                id=7, bk_cloud_id=CLOUD_ID, cluster_type=ClusterType.TendisTwemproxyRedisInstance
            )
            with patch.object(drill_mod.Cluster.objects, "get", return_value=cluster), patch.object(
                rfod, "get_instance_info", return_value={"ip": DRILL_IP, "logical_city_id": 1}
            ), patch.object(rfod, "get_drill_instances", return_value=set()), patch.object(
                drill_mod.Ticket, "create_ticket"
            ) as create_ticket:
                rfod.get_failover_drill_params()
                rfod.create_run_failover_drill_ticket()

        details = create_ticket.call_args.kwargs["details"]
        assert details["drill_infos"][0]["dbha_version"] == "v1,v2"

    @pytest.mark.usefixtures("multi_db")
    def test_v2_adopts_cluster_cloud(self):
        cluster = _create_cluster(bk_cloud_id=CLOUD_ID + 1)
        with patch.object(RedisFailoverDrill, "resolve_city_by_ip", return_value="深圳"):
            rfod = RedisFailoverDrill(
                city="",
                labels=[],
                bk_biz_id=BIZ_ID,
                bk_cloud_id=CLOUD_ID,
                city_map={},
                instance_type="proxy",
                version="v2",
                immute_domain=V2_DOMAIN,
            )
            with patch.object(
                rfod, "get_instance_info", return_value={"ip": DRILL_IP, "logical_city_id": 1}
            ) as instance_info:
                rfod.get_failover_drill_params()

        assert rfod.bk_cloud_id == cluster.bk_cloud_id
        assert instance_info.call_args.args[0].id == cluster.id
        assert rfod.failover_drill_info["drill_infos"][0]["bk_cloud_id"] == cluster.bk_cloud_id
        rpt = FailoverDrillReport.objects.get(main_task_id=rfod.main_task_id)
        assert (rpt.bk_cloud_id, rpt.city, rpt.version) == (cluster.bk_cloud_id, "深圳", "v2")

    def test_v2_cluster_type_from_config(self):
        cluster_type = ClusterType.TendisPredixyRedisCluster.value
        with patch.object(RedisFailoverDrill, "init_report"):
            rfod = RedisFailoverDrill(
                city="",
                labels=[],
                bk_biz_id=BIZ_ID,
                bk_cloud_id=CLOUD_ID,
                city_map={},
                instance_type="backend",
                version="v2",
                immute_domain=V2_DOMAIN,
                cluster_type=cluster_type,
            )
        assert rfod.cluster_type() == cluster_type
        assert rfod.cluster_filters()["cluster_type"] == cluster_type
        assert _drill().cluster_type() == ClusterType.TendisTwemproxyRedisInstance.value

    def test_v1_cluster_filters_include_cloud(self):
        assert _drill().cluster_filters()["bk_cloud_id"] == CLOUD_ID
        assert "bk_cloud_id" not in _drill(version="v2", immute_domain=V2_DOMAIN).cluster_filters()
        assert "bk_cloud_id" not in _drill(version="v1,v2", immute_domain=V2_DOMAIN).cluster_filters()

    def test_resolve_city_falls_back_to_dash(self):
        rfod = _drill()
        with patch.object(drill_mod.Machine.objects, "get", side_effect=drill_mod.Machine.DoesNotExist):
            assert rfod.resolve_city_by_ip(DRILL_IP) == "-"


class TestSendDrillAlert:
    def _send(self, chat_ids, handler=None):
        handler = handler or MagicMock()
        with patch.object(utils_mod, "load_chat_ids_by_priority", return_value=chat_ids) as load_ids, patch.object(
            utils_mod.AppCache.objects,
            "get",
            return_value=SimpleNamespace(bk_biz_name="biz", bk_biz_id=BIZ_ID, db_app_abbr="test"),
        ), patch.object(utils_mod.DBAdministrator, "get_biz_db_type_admins", return_value=["dba"]), patch.object(
            utils_mod, "CmsiHandler", return_value=handler
        ) as cmsi:
            utils_mod.send_drill_alert_to_qywx(
                city="深圳",
                bk_biz_id=BIZ_ID,
                cluster_domain=V2_DOMAIN,
                instance_type="proxy",
                drill_ip=DRILL_IP,
                failure_reason="x",
                task_status="y",
                version="v2",
            )
        return load_ids, cmsi, handler

    def test_alert_contains_version(self):
        _, cmsi, handler = self._send(["chat"])
        content = cmsi.call_args.args[1]
        assert "DBHA版本 : v2" in content
        assert cmsi.call_args.args[2] == ["chat"]
        handler.send_wecom_robot.assert_called_once()

    def test_alert_uses_l0_chat_ids(self):
        load_ids, cmsi, handler = self._send(["wrk-l0"])
        load_ids.assert_called_once_with("L0")
        assert cmsi.call_args.args[2] == ["wrk-l0"]
        handler.send_wecom_robot.assert_called_once()

    def test_alert_skips_when_no_chat_ids(self):
        _, cmsi, handler = self._send([])
        cmsi.assert_not_called()
        handler.send_wecom_robot.assert_not_called()


@pytest.fixture
def no_alert():
    with patch.object(drill_mod, "send_drill_alert_to_qywx") as alert:
        yield alert


def _create_cluster(**extra):
    data = {
        "name": "drill",
        "immute_domain": V2_DOMAIN,
        "bk_biz_id": BIZ_ID,
        "bk_cloud_id": CLOUD_ID,
        "cluster_type": ClusterType.TendisTwemproxyRedisInstance.value,
        "status": ClusterStatus.NORMAL.value,
    }
    data.update(extra)
    return Cluster.objects.create(**data)


def _report():
    return FailoverDrillReport.objects.order_by("-id").first()


V1_DOMAIN = "cache.failover-drill-sz.test.db"


class TestFailoverDrillUnitPrecheck:
    def _assert_aborted(self, no_alert, create_ticket, task_status):
        create_ticket.assert_not_called()
        no_alert.assert_called_once()
        rpt = _report()
        assert rpt.task_status == task_status
        assert rpt.state == ReportStateType.ABNORMAL

    @pytest.mark.usefixtures("multi_db")
    @pytest.mark.parametrize("cluster_extra", [{"bk_biz_id": BIZ_ID + 1}, {"bk_cloud_id": CLOUD_ID + 1}])
    def test_v1_cluster_mismatch_is_no_cluster(self, no_alert, cluster_extra):
        _create_cluster(immute_domain=V1_DOMAIN, **cluster_extra)
        with patch.object(drill_mod.Ticket, "create_ticket") as create_ticket:
            unit_mod.failover_drill_unit({"city": "深圳", "immute_domain": V1_DOMAIN}, _conf())

        self._assert_aborted(no_alert, create_ticket, TaskStatus.NO_CLUSTER)

    @pytest.mark.usefixtures("multi_db")
    @pytest.mark.parametrize(
        "cluster_extra",
        [{"bk_biz_id": BIZ_ID + 1}, {"cluster_type": ClusterType.TendisPredixyTendisplusCluster.value}],
    )
    def test_v2_cluster_mismatch_is_no_cluster(self, no_alert, cluster_extra):
        _create_cluster(**cluster_extra)
        with patch.object(drill_mod.Ticket, "create_ticket") as create_ticket:
            unit_mod.failover_drill_unit({"city": "", "immute_domain": V2_DOMAIN}, _conf(version="v2"))

        self._assert_aborted(no_alert, create_ticket, TaskStatus.NO_CLUSTER)

    @pytest.mark.usefixtures("multi_db")
    def test_v2_non_twemproxy_cluster_passes_precheck(self, no_alert):
        cluster_type = ClusterType.TendisPredixyRedisCluster.value
        _create_cluster(cluster_type=cluster_type)
        with patch.object(
            RedisFailoverDrill, "get_instance_info", return_value={"ip": DRILL_IP, "logical_city_id": 1}
        ), patch.object(RedisFailoverDrill, "resolve_city_by_ip", return_value="深圳"), patch.object(
            unit_mod, "get_dbha_v2_service_ips", return_value=[]
        ), patch.object(
            drill_mod.Ticket, "create_ticket"
        ) as create_ticket:
            unit_mod.failover_drill_unit(
                {"city": "", "immute_domain": V2_DOMAIN},
                _conf(version="v2", cluster_type=cluster_type, target_type="backend"),
            )

        create_ticket.assert_not_called()
        rpt = _report()
        assert (rpt.cluster_type, rpt.task_status) == (cluster_type, TaskStatus.NO_DBHA_V2_SERVICE_IP)

    @pytest.mark.usefixtures("multi_db")
    def test_v2_domain_not_found_is_no_cluster(self, no_alert):
        with patch.object(drill_mod.Ticket, "create_ticket") as create_ticket:
            unit_mod.failover_drill_unit({"city": "", "immute_domain": V2_DOMAIN}, _conf(version="v2"))

        self._assert_aborted(no_alert, create_ticket, TaskStatus.NO_CLUSTER)

    @pytest.mark.usefixtures("multi_db")
    def test_v2_empty_domain_aborts(self, no_alert):
        _create_cluster(immute_domain="cache.failover-drill-v2-sz.test.db")
        with patch.object(Cluster.objects, "get") as cluster_get, patch.object(
            drill_mod.Ticket, "create_ticket"
        ) as create_ticket:
            unit_mod.failover_drill_unit({"city": "", "immute_domain": ""}, _conf(version="v2"))

        cluster_get.assert_not_called()
        self._assert_aborted(no_alert, create_ticket, TaskStatus.NO_CLUSTER_DOMAIN)
        assert _report().cluster_domain == ""

    @pytest.mark.usefixtures("multi_db")
    def test_v2_cluster_cloud_differs_still_drills(self, no_alert):
        _create_cluster(bk_cloud_id=CLOUD_ID + 1)
        with patch.object(
            RedisFailoverDrill, "get_instance_info", return_value={"ip": DRILL_IP, "logical_city_id": 1}
        ), patch.object(RedisFailoverDrill, "resolve_city_by_ip", return_value="深圳"), patch.object(
            RedisFailoverDrill, "get_drill_instances", return_value=set()
        ), patch.object(
            RedisFailoverDrill, "get_dbha_info", return_value=({"error": ""}, False)
        ), patch.object(
            unit_mod, "get_dbha_v2_service_ips", return_value=["2.2.2.2"]
        ) as service_ips, patch.object(
            unit_mod, "autofix_ticket_polling", return_value=(False, -1)
        ), patch.object(
            drill_mod.Ticket, "create_ticket"
        ) as create_ticket:
            unit_mod.failover_drill_unit(
                {"city": "", "immute_domain": V2_DOMAIN}, _conf(version="v2", max_retry=1, interval=0)
            )

        service_ips.assert_called_once_with(CLOUD_ID + 1, 1)
        create_ticket.assert_called_once()
        assert create_ticket.call_args.kwargs["details"]["drill_infos"][0]["bk_cloud_id"] == CLOUD_ID + 1
        rpt = _report()
        assert (rpt.bk_cloud_id, rpt.city) == (CLOUD_ID + 1, "深圳")

    @pytest.mark.usefixtures("multi_db")
    def test_v2_empty_service_ips_no_ticket(self, no_alert):
        _create_cluster()
        with patch.object(RedisFailoverDrill, "get_failover_drill_params"), patch.object(
            RedisFailoverDrill, "get_drill_logical_city_id", return_value=1
        ), patch.object(RedisFailoverDrill, "get_drill_ip", return_value=DRILL_IP), patch.object(
            unit_mod, "get_dbha_v2_service_ips", return_value=[]
        ) as service_ips, patch.object(
            drill_mod.Ticket, "create_ticket"
        ) as create_ticket:
            unit_mod.failover_drill_unit({"city": "", "immute_domain": V2_DOMAIN}, _conf(version="v2"))

        service_ips.assert_called_once_with(CLOUD_ID, 1)
        create_ticket.assert_not_called()
        no_alert.assert_called_once()
        rpt = _report()
        assert rpt.task_status == TaskStatus.NO_DBHA_V2_SERVICE_IP
        assert rpt.state == ReportStateType.ABNORMAL
        assert "拿不到 dbha-v2 服务 IP" in rpt.task_info

    @pytest.mark.usefixtures("multi_db")
    def test_v2_ha_servers_unavailable_logs_and_sends_alert(self, no_alert):
        _create_cluster()
        with patch.object(RedisFailoverDrill, "get_failover_drill_params"), patch.object(
            RedisFailoverDrill, "get_drill_logical_city_id", return_value=1
        ), patch.object(RedisFailoverDrill, "get_drill_ip", return_value=DRILL_IP), patch.object(
            failover_drill_dbha.HADBApiV2, "ha_servers", side_effect=Exception("ha-servers unavailable")
        ), patch.object(
            drill_mod.Ticket, "create_ticket"
        ) as create_ticket:
            unit_mod.failover_drill_unit({"city": "", "immute_domain": V2_DOMAIN}, _conf(version="v2"))

        create_ticket.assert_not_called()
        no_alert.assert_called_once()
        assert no_alert.call_args.kwargs["task_status"] == TaskStatus.NO_DBHA_V2_SERVICE_IP
        assert "拿不到 dbha-v2 服务 IP" in no_alert.call_args.kwargs["failure_reason"]
        rpt = _report()
        assert rpt.task_status == TaskStatus.NO_DBHA_V2_SERVICE_IP
        assert rpt.state == ReportStateType.ABNORMAL
        assert "拿不到 dbha-v2 服务 IP" in rpt.task_info


class TestFailoverDrillUnitResult:
    @pytest.mark.usefixtures("multi_db")
    @pytest.mark.parametrize(
        "version, autofix_generated, autofix_done, switch_success, state, task_status",
        [
            ("v1", False, None, True, ReportStateType.ABNORMAL, TaskStatus.SWITCHED_NO_AUTOFIX),
            ("v1", True, False, True, ReportStateType.ABNORMAL, TaskStatus.SWITCHED_AUTOFIX_ERROR),
            ("v2", False, None, True, ReportStateType.WARNING, TaskStatus.SWITCHED_NO_AUTOFIX),
            ("v2", True, False, True, ReportStateType.WARNING, TaskStatus.SWITCHED_AUTOFIX_ERROR),
            ("v1,v2", False, None, True, ReportStateType.WARNING, TaskStatus.SWITCHED_NO_AUTOFIX),
            ("v2,v1", True, False, True, ReportStateType.WARNING, TaskStatus.SWITCHED_AUTOFIX_ERROR),
            ("v2", False, None, False, ReportStateType.ABNORMAL, TaskStatus.SWITCH_FAILED),
            ("v1", True, True, True, ReportStateType.NORMAL, TaskStatus.SUCCESS),
        ],
    )
    def test_result_classification(
        self, no_alert, version, autofix_generated, autofix_done, switch_success, state, task_status
    ):
        _create_cluster()
        with patch.object(RedisFailoverDrill, "get_failover_drill_params"), patch.object(
            RedisFailoverDrill, "get_drill_logical_city_id", return_value=1
        ), patch.object(RedisFailoverDrill, "get_drill_ip", return_value=DRILL_IP), patch.object(
            RedisFailoverDrill, "create_run_failover_drill_ticket"
        ), patch.object(
            RedisFailoverDrill, "get_dbha_info", return_value=({"error": ""}, switch_success)
        ), patch.object(
            RedisFailoverDrill, "update_drill_report"
        ), patch.object(
            unit_mod, "get_dbha_v2_service_ips", return_value=["2.2.2.2"]
        ), patch.object(
            unit_mod, "autofix_ticket_polling", return_value=(autofix_generated, 1 if autofix_generated else -1)
        ), patch.object(
            unit_mod, "autofix_done_polling", return_value=autofix_done
        ):
            unit_mod.failover_drill_unit(
                {"city": "", "immute_domain": V2_DOMAIN}, _conf(version=version, max_retry=1, interval=0)
            )

        rpt = _report()
        assert rpt.state == state
        assert rpt.task_status == task_status
        assert no_alert.called == (state != ReportStateType.NORMAL)
        if state == ReportStateType.WARNING:
            assert "dbha-v2 自愈未发生" in rpt.task_info

    @pytest.mark.usefixtures("multi_db")
    def test_query_failed_is_not_switch_failed(self, no_alert):
        _create_cluster()
        with patch.object(RedisFailoverDrill, "get_failover_drill_params"), patch.object(
            RedisFailoverDrill, "get_drill_logical_city_id", return_value=1
        ), patch.object(RedisFailoverDrill, "get_drill_ip", return_value=DRILL_IP), patch.object(
            RedisFailoverDrill, "create_run_failover_drill_ticket"
        ), patch.object(
            RedisFailoverDrill, "get_dbha_switch_data", side_effect=Exception("dbha-v2 down")
        ), patch.object(
            unit_mod, "get_dbha_v2_service_ips", return_value=["2.2.2.2"]
        ), patch.object(
            unit_mod, "autofix_ticket_polling", return_value=(False, -1)
        ):
            unit_mod.failover_drill_unit(
                {"city": "", "immute_domain": V2_DOMAIN}, _conf(version="v2", max_retry=1, interval=0)
            )

        rpt = _report()
        assert (rpt.state, rpt.task_status) == (ReportStateType.ABNORMAL, TaskStatus.DBHA_QUERY_FAILED)
        assert rpt.dbha_status == DBHASwitchResult.FAIL
        assert "dbha-v2 down" in no_alert.call_args.kwargs["failure_reason"]


class TestDispatch:
    @pytest.fixture
    def rows(self, db):
        cluster_type = ClusterType.TendisTwemproxyRedisInstance.value
        FailoverDrillConfig.objects.create(
            labels=[], cluster_type=cluster_type, city_map={"深圳": "sz"}, switch_flag=True, bk_biz_id=BIZ_ID
        )
        FailoverDrillConfig.objects.create(
            labels=[],
            cluster_type=cluster_type,
            city_map={"深圳": "sz"},
            switch_flag=True,
            bk_biz_id=BIZ_ID,
            version="v2",
            cluster_domain=V2_DOMAIN,
        )

    @pytest.mark.parametrize(
        "enable_v2, expected_domains",
        [(True, ["cache.failover-drill-sz.test.db", V2_DOMAIN]), (False, ["cache.failover-drill-sz.test.db"])],
    )
    def test_dispatch_by_row(self, rows, enable_v2, expected_domains):
        with patch.object(task_mod.env, "ENABLE_DBHA_V2", enable_v2), patch.object(
            drill_mod.AppCache.objects, "get", return_value=SimpleNamespace(db_app_abbr="test")
        ), patch.object(task_mod.failover_drill_unit, "apply_async") as apply_async:
            task_mod.proxy_failover_drill_task()

        calls = [c.kwargs["args"] for c in apply_async.call_args_list]
        assert [target["immute_domain"] for target, _ in calls] == expected_domains
        for target, conf in calls:
            assert conf["target_type"] == "proxy"
            assert conf["version"] == ("v2" if target["immute_domain"] == V2_DOMAIN else "v1")

    def test_combined_row_dispatches_once_with_canonical_version(self, db):
        cluster_type = ClusterType.TendisTwemproxyRedisInstance.value
        FailoverDrillConfig.objects.create(
            labels=[], cluster_type=cluster_type, city_map={"深圳": "sz"}, switch_flag=True, bk_biz_id=BIZ_ID
        )
        FailoverDrillConfig.objects.create(
            labels=[],
            cluster_type=cluster_type,
            switch_flag=True,
            bk_biz_id=BIZ_ID,
            version="v2",
            cluster_domain="cache.v2-only.test.db",
        )
        FailoverDrillConfig.objects.create(
            labels=[],
            cluster_type=cluster_type,
            switch_flag=True,
            bk_biz_id=BIZ_ID,
            version="v2,v1",
            cluster_domain=V2_DOMAIN,
        )
        with patch.object(task_mod.env, "ENABLE_DBHA_V2", True), patch.object(
            drill_mod.AppCache.objects, "get", return_value=SimpleNamespace(db_app_abbr="test")
        ), patch.object(task_mod.failover_drill_unit, "apply_async") as apply_async:
            task_mod.proxy_failover_drill_task()

        calls = [c.kwargs["args"] for c in apply_async.call_args_list]
        domains = [target["immute_domain"] for target, _ in calls]
        assert domains.count(V2_DOMAIN) == 1
        assert "cache.failover-drill-sz.test.db" in domains
        assert "cache.v2-only.test.db" in domains
        combined = [conf for target, conf in calls if target["immute_domain"] == V2_DOMAIN]
        assert len(combined) == 1
        assert combined[0]["version"] == "v1,v2"

    def test_combined_skipped_when_v2_disabled(self, db):
        FailoverDrillConfig.objects.create(
            labels=[],
            cluster_type=ClusterType.TendisTwemproxyRedisInstance.value,
            switch_flag=True,
            bk_biz_id=BIZ_ID,
            version="v1,v2",
            cluster_domain=V2_DOMAIN,
        )
        with patch.object(task_mod.env, "ENABLE_DBHA_V2", False), patch.object(
            task_mod.failover_drill_unit, "apply_async"
        ) as apply_async:
            task_mod.proxy_failover_drill_task()
        apply_async.assert_not_called()

    @pytest.mark.parametrize(
        "target_type, task_name, expected",
        [
            ("proxy", "proxy_failover_drill_task", {"v2-predixy"}),
            ("backend", "redis_failover_drill_task", {"v2-predixy", "v2-redis-instance"}),
        ],
    )
    def test_v2_cluster_types(self, db, target_type, task_name, expected):
        rows = {
            "v2-predixy": ("v2", ClusterType.TendisPredixyRedisCluster.value),
            "v2-redis-instance": ("v2", ClusterType.TendisRedisInstance.value),
            "v2-unsupported": ("v2", ClusterType.TendisTendisplusCluster.value),
            "v1-predixy": ("v1", ClusterType.TendisPredixyRedisCluster.value),
        }
        for domain, (version, cluster_type) in rows.items():
            FailoverDrillConfig.objects.create(
                labels=[],
                cluster_type=cluster_type,
                switch_flag=True,
                bk_biz_id=BIZ_ID,
                version=version,
                cluster_domain=domain,
                city_map={"深圳": "sz"},
            )

        with patch.object(task_mod.env, "ENABLE_DBHA_V2", True), patch.object(
            drill_mod.AppCache.objects, "get", return_value=SimpleNamespace(db_app_abbr="test")
        ), patch.object(task_mod.failover_drill_unit, "apply_async") as apply_async:
            getattr(task_mod, task_name)()

        calls = [c.kwargs["args"] for c in apply_async.call_args_list]
        assert {target["immute_domain"] for target, _ in calls} == expected
        for target, conf in calls:
            assert conf["target_type"] == target_type
            assert conf["cluster_type"] == rows[target["immute_domain"]][1]

    def test_no_config_returns(self, db):
        with patch.object(task_mod.failover_drill_unit, "apply_async") as apply_async:
            task_mod.redis_failover_drill_task()
        apply_async.assert_not_called()

    def test_only_disabled_config_returns(self, db):
        FailoverDrillConfig.objects.create(
            labels=[], cluster_type=ClusterType.TendisTwemproxyRedisInstance.value, switch_flag=False
        )
        with patch.object(task_mod.failover_drill_unit, "apply_async") as apply_async:
            task_mod.redis_failover_drill_task()
        apply_async.assert_not_called()


class TestDeleteOutdatedRecords:
    @pytest.mark.usefixtures("multi_db")
    def test_deletes_old_reports_of_all_drill_types(self):
        for i, cluster_type in enumerate(
            [ClusterType.TendisTwemproxyRedisInstance.value, ClusterType.TendisPredixyRedisCluster.value]
        ):
            FailoverDrillReport.objects.create(bk_biz_id=BIZ_ID, cluster_type=cluster_type, main_task_id=f"old{i}")
        FailoverDrillReport.objects.create(
            bk_biz_id=BIZ_ID, cluster_type=ClusterType.TenDBHA.value, main_task_id="mysql"
        )
        FailoverDrillReport.objects.update(create_at="2000-01-01T00:00:00Z")

        task_mod.delete_outdated_drill_records()

        assert list(FailoverDrillReport.objects.values_list("main_task_id", flat=True)) == ["mysql"]


class TestMysqlConfigRead:
    def test_mysql_reads_only_v1_row(self, db):
        cluster_type = ClusterType.TenDBHA.value
        FailoverDrillConfig.objects.create(labels=[], cluster_type=cluster_type, switch_flag=False)
        FailoverDrillConfig.objects.create(labels=[], cluster_type=cluster_type, switch_flag=True, version="v2")
        FailoverDrillConfig.objects.create(labels=[], cluster_type=cluster_type, switch_flag=True, version="v1,v2")

        with patch.object(mysql_unit_mod, "MysqlFailoverDrill") as drill:
            mysql_unit_mod.ha_failover_drill_unit("深圳")

        drill.assert_not_called()
