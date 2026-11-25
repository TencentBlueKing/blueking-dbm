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
import copy
from unittest.mock import MagicMock, patch

from django.test import TestCase

from backend.db_meta.enums import ClusterStatus, ClusterType
from backend.db_meta.enums.comm import SystemTagEnum, TagType
from backend.db_meta.models import Cluster, Tag
from backend.db_monitor.views.callbacks import mysql as mysql_callback
from backend.db_monitor.views.callbacks.base import AlarmCallback
from backend.db_monitor.views.callbacks.mysql import MySQLAlarm

CALLBACK_DATA_TEMPLATE = {
    "appointees": ["admin"],
    "callback_message": {
        "current_value": "100",
        "description": "MySQL 实例 Threads_running >= 100",
        "type": "alarm",
        "latest_anomaly_record": {
            "create_time": "2026-10-14 01:00:00",
            "origin_alarm": {"anomaly": {"1": {"anomaly_message": "当前值 100", "anomaly_time": "2026-10-14 01:00:00"}}},
        },
        "event": {
            "level": 1,
            "begin_time": "2026-10-14 00:55:00",
            "create_time": "2026-10-14 00:55:00",
            "agg_dimensions": ["cluster_domain"],
            "dimensions": {
                "appid": "3",
                "cluster_domain": "plain-ha.test.db",
                "cluster_type": ClusterType.TenDBHA.value,
                "bk_target_ip": "127.0.0.1",
            },
        },
        "strategy": {"name": "MySQL 实例 Threads_running"},
        "related_info": {},
    },
}


def make_callback_data(cluster_domain, strategy_name="MySQL 实例 Threads_running", dimensions_override=None):
    data = copy.deepcopy(CALLBACK_DATA_TEMPLATE)
    data["callback_message"]["strategy"]["name"] = strategy_name
    dimensions = data["callback_message"]["event"]["dimensions"]
    dimensions["cluster_domain"] = cluster_domain
    if dimensions_override:
        dimensions.update(dimensions_override)
    return data


class TestMySQLAlarmCallbackIgnoreClusters(TestCase):
    def _create_cluster(self, name, status=ClusterStatus.NORMAL.value, cluster_type=ClusterType.TenDBHA.value):
        return Cluster.objects.create(
            bk_biz_id=3,
            cluster_type=cluster_type,
            name=name,
            immute_domain="{}.test.db".format(name),
            status=status,
        )

    def _create_tag(self, key, is_builtin=True, bk_biz_id=0):
        return Tag.objects.create(
            bk_biz_id=bk_biz_id,
            key=key,
            value="True",
            type=TagType.CLUSTER,
            is_builtin=is_builtin,
        )

    def _dispatch(self, callback_data):
        alarm_handler = MagicMock()
        slowlog_handler = MagicMock()
        conf_handler = MagicMock()
        with patch.dict(
            mysql_callback.__dict__,
            {
                "call_mysql_alarm_analyzer": alarm_handler,
                "call_slowlog_ai_analysis": slowlog_handler,
                "call_mysql_conf_analyzer": conf_handler,
            },
        ):
            with patch.object(AlarmCallback, "check_rate_limit", return_value=True) as mock_rate_limit:
                MySQLAlarm.callback(callback_data)
        return alarm_handler, slowlog_handler, conf_handler, mock_rate_limit

    def test_normal_cluster_dispatches(self):
        cluster = self._create_cluster("normal-ha")
        data = make_callback_data(cluster.immute_domain)

        alarm_handler, unused_slowlog, unused_conf, mock_rate_limit = self._dispatch(data)

        alarm_handler.delay.assert_called_once()
        mock_rate_limit.assert_called_once()

    def test_builtin_temporary_tag_cluster_skipped(self):
        cluster = self._create_cluster("temp-tag-ha")
        cluster.tags.add(self._create_tag(SystemTagEnum.TEMPORARY.value, is_builtin=True))
        data = make_callback_data(cluster.immute_domain, strategy_name="主机 CPU 负载")

        alarm_handler, slowlog_handler, conf_handler, mock_rate_limit = self._dispatch(data)

        alarm_handler.delay.assert_not_called()
        slowlog_handler.delay.assert_not_called()
        conf_handler.delay.assert_not_called()
        mock_rate_limit.assert_not_called()

    def test_builtin_exercise_tag_cluster_skipped(self):
        cluster = self._create_cluster("exercise-single", cluster_type=ClusterType.TenDBSingle.value)
        cluster.tags.add(self._create_tag(SystemTagEnum.EXERCISE.value, is_builtin=True))
        data = make_callback_data(
            cluster.immute_domain,
            strategy_name="慢查询数量",
            dimensions_override={"cluster_type": ClusterType.TenDBSingle.value},
        )

        alarm_handler, slowlog_handler, conf_handler, mock_rate_limit = self._dispatch(data)

        alarm_handler.delay.assert_not_called()
        slowlog_handler.delay.assert_not_called()
        conf_handler.delay.assert_not_called()
        mock_rate_limit.assert_not_called()

    def test_temporary_status_cluster_skipped(self):
        cluster = self._create_cluster("legacy-temp-ha", status=ClusterStatus.TEMPORARY.value)
        data = make_callback_data(cluster.immute_domain)

        alarm_handler, unused_slowlog, unused_conf, mock_rate_limit = self._dispatch(data)

        alarm_handler.delay.assert_not_called()
        mock_rate_limit.assert_not_called()

    def test_custom_non_builtin_temporary_tag_not_skipped(self):
        cluster = self._create_cluster("custom-tag-ha")
        cluster.tags.add(self._create_tag(SystemTagEnum.TEMPORARY.value, is_builtin=False, bk_biz_id=3))
        data = make_callback_data(cluster.immute_domain)

        alarm_handler, unused_slowlog, unused_conf, mock_rate_limit = self._dispatch(data)

        alarm_handler.delay.assert_called_once()
        mock_rate_limit.assert_called_once()

    def test_missing_dimensions_backfills_from_cluster(self):
        cluster = self._create_cluster("backfill-ha")
        data = make_callback_data(
            cluster.immute_domain,
            dimensions_override={"appid": "0", "cluster_type": ""},
        )

        alarm_handler, unused_slowlog, unused_conf, unused_rate_limit = self._dispatch(data)

        alarm_handler.delay.assert_called_once()
        alarm_base_info = alarm_handler.delay.call_args[0][1]
        self.assertEqual(alarm_base_info["bk_biz_id"], cluster.bk_biz_id)
        self.assertEqual(alarm_base_info["cluster_type"], cluster.cluster_type)

    def test_missing_cluster_in_db_does_not_raise(self):
        data = make_callback_data(
            "nonexistent.test.db",
            dimensions_override={"appid": "0", "cluster_type": ""},
        )

        alarm_handler, unused_slowlog, unused_conf, unused_rate_limit = self._dispatch(data)

        alarm_handler.delay.assert_called_once()
