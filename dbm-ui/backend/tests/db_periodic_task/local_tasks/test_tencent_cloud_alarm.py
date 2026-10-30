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
import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase


def _load_alarm_modules():
    """按文件加载告警模块，不 import local_tasks 包。

    local_tasks 之外的代码会从该包取出 register_periodic_task 等名字。
    测试不能把这个包换成空模块，也不能在导入时执行它的 __init__.py。
    """
    pkg_name = "tencent_cloud_alarm_under_test"
    root = Path(__file__).resolve().parents[3] / "db_periodic_task" / "local_tasks" / "tencent_cloud_alarm"
    package = types.ModuleType(pkg_name)
    package.__path__ = [str(root)]
    package.__package__ = pkg_name
    package.__file__ = str(root / "__init__.py")
    sys.modules[pkg_name] = package

    def load(mod_name):
        full_name = "{}.{}".format(pkg_name, mod_name)
        spec = importlib.util.spec_from_file_location(full_name, root / "{}.py".format(mod_name))
        module = importlib.util.module_from_spec(spec)
        module.__package__ = pkg_name
        sys.modules[full_name] = module
        spec.loader.exec_module(module)
        setattr(package, mod_name, module)
        return module

    return load("client"), load("sync")


client_mod, sync_mod = _load_alarm_modules()
fetch_alarm_histories = client_mod.fetch_alarm_histories
build_event = sync_mod.build_event
build_row = sync_mod.build_row
parse_instance = sync_mod.parse_instance
resolve_start = sync_mod.resolve_start
sync_tencent_cloud_alarms = sync_mod.sync_tencent_cloud_alarms
sync_tencent_cloud_alarms_guarded = sync_mod.sync_tencent_cloud_alarms_guarded
to_record = sync_mod.to_record


def _history(alarm_id, status="ALARM", vip="127.0.0.1"):
    return {
        "FirstOccurTime": 1790000000,
        "AlarmType": "METRIC",
        "AlarmStatus": status,
        "Region": "ap-guangzhou",
        "PolicyName": "默认",
        "AlarmObject": "Name:lb-demo|VpcId:vpc-demo|Vip:{}".format(vip),
        "Content": "入带宽利用率 > 80%",
        "AlarmId": alarm_id,
        "Dimensions": "",
    }


class TencentCloudAlarmSyncTests(SimpleTestCase):
    def test_import_does_not_replace_local_tasks_package(self):
        pkg = sys.modules.get("backend.db_periodic_task.local_tasks")
        if pkg is None:
            return
        self.assertTrue(getattr(pkg, "__file__", None))

    def test_parse_instance_from_alarm_object(self):
        parsed = parse_instance("Name:lb-demo|VpcId:vpc-demo|Vip:127.0.0.1")
        self.assertEqual(parsed["实例名称"], "lb-demo")
        self.assertEqual(parsed["实例地址"], "127.0.0.1")

    def test_parse_address_keeps_nonzero_port(self):
        parsed = parse_instance("IpPort:127.0.0.1:8080|Vip:127.0.0.2")
        self.assertEqual(parsed["实例地址"], "127.0.0.1:8080")

    def test_to_record_uses_product_code(self):
        record = to_record(_history("alarm-1"))
        self.assertEqual(record["产品"], "clb")
        redis_item = _history("alarm-redis")
        redis_item["_product"] = "redis"
        self.assertEqual(to_record(redis_item)["产品"], "redis")
        self.assertEqual(record["告警ID"], "alarm-1")
        self.assertEqual(record["状态"], "ALARM")
        self.assertEqual(record["timestamp_ms"], 1790000000 * 1000)

    def test_alarm_level_comes_from_alarm_level_field(self):
        warning = _history("alarm-warn")
        warning["AlarmLevel"] = "Warn"
        critical = _history("alarm-serious")
        critical["AlarmLevel"] = "Serious"
        critical["Content"] = "丢弃出带宽 > 10 Bit/s"
        remind = _history("alarm-remind")
        remind["AlarmLevel"] = "Remind"
        warning_record = to_record(warning)
        critical_record = to_record(critical)
        self.assertEqual(warning_record["级别"], "warning")
        self.assertEqual(to_record(remind)["级别"], "warning")
        self.assertEqual(critical_record["级别"], "critical")
        self.assertEqual(build_event(warning_record, None).dimension["alarm_level"], "warning")
        self.assertEqual(build_event(critical_record, None).dimension["alarm_level"], "critical")

    def test_resolve_start_looks_back_one_day_then_overlaps(self):
        self.assertEqual(resolve_start(0, 1000000), 1000000 - 24 * 60 * 60)
        self.assertEqual(resolve_start(1000000, 1000100), 1000000 - 180)

    def test_build_row_without_cluster_is_not_an_event(self):
        row = build_row(to_record(_history("alarm-1")), None)
        self.assertEqual(row.alarm_id, "alarm-1")
        self.assertEqual(row.address, "127.0.0.1")
        self.assertEqual(row.content, "入带宽利用率 > 80%")
        self.assertEqual(row.product, "clb")
        self.assertEqual(row.cluster_id, 0)
        self.assertEqual(row.bk_biz_id, 0)
        self.assertFalse(row.event_sent)

    def test_build_row_copies_matched_cluster(self):
        cluster = SimpleNamespace(
            id=9, bk_biz_id=3, immute_domain="gamedb.demo.db", cluster_type="tendbha", db_app_abbr="demo"
        )
        row = build_row(to_record(_history("alarm-1")), cluster)
        self.assertEqual(row.cluster_id, 9)
        self.assertEqual(row.bk_biz_id, 3)
        self.assertEqual(row.cluster_domain, "gamedb.demo.db")
        self.assertEqual(row.cluster_type, "tendbha")
        self.assertEqual(row.app, "demo")

    @patch.object(sync_mod, "load_unsent_rows", return_value=[])
    @patch.object(sync_mod, "persist_rows")
    @patch.object(sync_mod, "existing_alarm_ids", return_value=set())
    @patch.object(sync_mod, "save_state")
    @patch.object(sync_mod, "cluster_by_vip", return_value={})
    @patch.object(sync_mod.BKMonitorV3EventApi, "send_event")
    @patch.object(sync_mod, "collect_histories")
    @patch.object(sync_mod, "load_state")
    @patch.object(sync_mod, "load_credentials")
    def test_unmatched_vip_is_stored_without_event(
        self,
        load_credentials,
        load_state,
        fetch_histories,
        send_event,
        cluster_by_vip,
        save_state,
        existing_alarm_ids,
        persist_rows,
        load_unsent_rows,
    ):
        load_credentials.return_value = object()
        load_state.return_value = {"watermark": 0}
        fetch_histories.return_value = (
            [_history("alarm-1"), _history("alarm-1"), _history("alarm-ok", status="OK")],
            None,
        )

        added = sync_tencent_cloud_alarms(now=1790000100)

        self.assertEqual(added, 2)
        send_event.assert_not_called()
        rows = persist_rows.call_args[0][0]
        self.assertEqual([row.alarm_id for row in rows], ["alarm-1", "alarm-ok"])
        self.assertTrue(all(row.cluster_id == 0 for row in rows))
        self.assertEqual(save_state.call_args[0][0]["watermark"], 1790000100)
        cluster_by_vip.assert_called_once()
        existing_alarm_ids.assert_called_once()
        load_unsent_rows.assert_called_once()

    @patch.object(sync_mod, "mark_event_sent")
    @patch.object(sync_mod, "load_unsent_rows", return_value=[])
    @patch.object(sync_mod, "persist_rows")
    @patch.object(sync_mod, "existing_alarm_ids", return_value=set())
    @patch.object(sync_mod, "save_state")
    @patch.object(sync_mod.BKMonitorV3EventApi, "send_event")
    @patch.object(sync_mod, "collect_histories")
    @patch.object(sync_mod, "load_state")
    @patch.object(sync_mod, "load_credentials")
    def test_matched_vip_is_stored_and_sent(
        self,
        load_credentials,
        load_state,
        fetch_histories,
        send_event,
        save_state,
        existing_alarm_ids,
        persist_rows,
        load_unsent_rows,
        mark_event_sent,
    ):
        cluster = SimpleNamespace(id=9, bk_biz_id=3, immute_domain="gamedb.demo.db", cluster_type="tendbha")
        load_credentials.return_value = object()
        load_state.return_value = {"watermark": 0}
        fetch_histories.return_value = (
            [_history("alarm-match", vip="127.0.0.1"), _history("alarm-miss", vip="127.0.0.2")],
            None,
        )

        with patch.object(sync_mod, "cluster_by_vip", return_value={"127.0.0.1": cluster}):
            added = sync_tencent_cloud_alarms(now=1790000100)

        self.assertEqual(added, 2)
        rows = persist_rows.call_args[0][0]
        self.assertEqual([row.alarm_id for row in rows], ["alarm-match", "alarm-miss"])
        self.assertEqual(rows[0].cluster_domain, "gamedb.demo.db")
        self.assertEqual(rows[1].cluster_id, 0)
        events = send_event.call_args[0][0]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].dimension["alarm_id"], "alarm-match")
        self.assertEqual(events[0].dimension["appid"], 3)
        self.assertEqual(events[0].dimension["cluster_domain"], "gamedb.demo.db")
        mark_event_sent.assert_called_once_with(["alarm-match"])
        self.assertEqual(save_state.call_args[0][0]["watermark"], 1790000100)
        existing_alarm_ids.assert_called_once()
        load_unsent_rows.assert_called_once()

    @patch.object(sync_mod, "save_state")
    @patch.object(sync_mod.BKMonitorV3EventApi, "send_event")
    @patch.object(sync_mod, "collect_histories")
    @patch.object(sync_mod, "load_credentials")
    def test_skip_without_credentials(self, load_credentials, fetch_histories, send_event, save_state):
        load_credentials.return_value = None

        added = sync_tencent_cloud_alarms(now=1790000100)

        self.assertEqual(added, 0)
        fetch_histories.assert_not_called()
        send_event.assert_not_called()
        save_state.assert_not_called()

    @patch.object(sync_mod, "save_state")
    @patch.object(sync_mod.BKMonitorV3EventApi, "send_event")
    @patch.object(sync_mod, "collect_histories")
    @patch.object(sync_mod, "load_state")
    @patch.object(sync_mod, "load_credentials")
    def test_api_error_does_not_advance_watermark(
        self, load_credentials, load_state, fetch_histories, send_event, save_state
    ):
        load_credentials.return_value = object()
        load_state.return_value = {"watermark": 100}
        fetch_histories.return_value = ([], True)

        added = sync_tencent_cloud_alarms(now=1790000100)

        self.assertEqual(added, 0)
        send_event.assert_not_called()
        save_state.assert_not_called()

    @patch.object(sync_mod, "cache")
    @patch.object(sync_mod, "sync_tencent_cloud_alarms")
    def test_skips_when_previous_run_still_active(self, sync_alarms, cache):
        cache.add.return_value = False

        sync_tencent_cloud_alarms_guarded()

        sync_alarms.assert_not_called()
        cache.delete.assert_not_called()

    @patch.object(sync_mod, "cache")
    @patch.object(sync_mod, "sync_tencent_cloud_alarms")
    def test_releases_lock_after_sync(self, sync_alarms, cache):
        cache.add.return_value = True

        sync_tencent_cloud_alarms_guarded()

        sync_alarms.assert_called_once()
        cache.delete.assert_called_once()

    @patch.object(sync_mod, "fetch_redis_tags")
    @patch.object(sync_mod, "mark_event_sent")
    @patch.object(sync_mod, "load_unsent_rows", return_value=[])
    @patch.object(sync_mod, "persist_rows")
    @patch.object(sync_mod, "existing_alarm_ids", return_value=set())
    @patch.object(sync_mod, "save_state")
    @patch.object(sync_mod.BKMonitorV3EventApi, "send_event")
    @patch.object(sync_mod, "collect_histories")
    @patch.object(sync_mod, "load_state")
    @patch.object(sync_mod, "load_credentials")
    def test_redis_alarm_is_stored_without_event(
        self,
        load_credentials,
        load_state,
        fetch_histories,
        send_event,
        save_state,
        existing_alarm_ids,
        persist_rows,
        load_unsent_rows,
        mark_event_sent,
        fetch_redis_tags,
    ):
        cluster = SimpleNamespace(id=9, bk_biz_id=3, immute_domain="gamedb.demo.db", cluster_type="tendbha")
        redis_item = _history("alarm-redis", vip="127.0.0.3")
        redis_item["_product"] = "redis"
        redis_item["AlarmObject"] = "InstanceId:crs-demo|InstanceName:redis-demo|Vip:127.0.0.1"
        load_credentials.return_value = object()
        load_state.return_value = {"watermark": 0}
        fetch_histories.return_value = ([_history("alarm-match"), redis_item], False)
        fetch_redis_tags.return_value = {"crs-demo": [{"键": "biz", "值": "demo"}]}

        with patch.object(sync_mod, "cluster_by_vip", return_value={"127.0.0.1": cluster}) as cluster_by_vip:
            added = sync_tencent_cloud_alarms(now=1790000100)

        self.assertEqual(added, 2)
        rows = persist_rows.call_args[0][0]
        self.assertEqual([row.product for row in rows], ["clb", "redis"])
        self.assertEqual(rows[0].cluster_domain, "gamedb.demo.db")
        self.assertEqual(rows[1].cluster_id, 0)
        self.assertEqual(rows[1].instance_id, "crs-demo")
        self.assertEqual(rows[1].tags, [{"键": "biz", "值": "demo"}])
        self.assertFalse(rows[1].event_sent)
        events = send_event.call_args[0][0]
        self.assertEqual([event.dimension["alarm_id"] for event in events], ["alarm-match"])
        mark_event_sent.assert_called_once_with(["alarm-match"])
        cluster_by_vip.assert_called_once_with({"127.0.0.1"})
        fetch_redis_tags.assert_called_once()
        existing_alarm_ids.assert_called_once()
        load_unsent_rows.assert_called_once()
        save_state.assert_called_once()

    def test_fetch_paginates_until_short_page(self):
        pages = {
            1: {"Response": {"TotalCount": 150, "Histories": [{"AlarmId": "a{}".format(i)} for i in range(100)]}},
            2: {"Response": {"TotalCount": 150, "Histories": [{"AlarmId": "b{}".format(i)} for i in range(50)]}},
        }

        def request_page(credential, start, end, page_number, namespace):
            self.assertEqual(namespace, "private_lb_client_to_lb_other")
            return pages[page_number]

        with patch.object(client_mod, "request_page", side_effect=request_page):
            histories, error = fetch_alarm_histories(object(), "private_lb_client_to_lb_other", 1, 2)

        self.assertIsNone(error)
        self.assertEqual(len(histories), 150)
        self.assertEqual(histories[0]["AlarmId"], "a0")
        self.assertEqual(histories[-1]["AlarmId"], "b49")
