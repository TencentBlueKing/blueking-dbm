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

from django.test import SimpleTestCase

from backend.db_meta.enums.comm import SystemTagEnum, TagType
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.ticket.constants import TicketType

CREATE_PATH = "backend.flow.utils.mysql.mysql_db_meta.TenDBSingleClusterHandler.create"
GET_CLUSTER_PATH = "backend.flow.utils.mysql.mysql_db_meta.Cluster.objects.get"
GET_TAG_PATH = "backend.flow.utils.mysql.mysql_db_meta.Tag.get_builtin_tag"


class TestMysqlSingleApplyExerciseTag(SimpleTestCase):
    def _ticket_data(self, ticket_type):
        return {
            "bk_biz_id": 3,
            "db_version": "MySQL-5.7",
            "clusters": [
                {"name": "exercise-a", "master": "rb-exercise-a.db"},
                {"name": "exercise-b", "master": "rb-exercise-b.db"},
            ],
            "module": 1,
            "created_by": "admin",
            "bk_cloud_id": 0,
            "city": "default",
            "ticket_type": ticket_type,
        }

    def _cluster(self):
        return {
            "new_ip": "127.0.0.2",
            "time_zone_info": {"time_zone": "Asia/Shanghai"},
        }

    def test_single_apply_with_exercise_tag(self):
        exercise_tag = MagicMock(name="exercise_tag")
        cluster_row = MagicMock(name="cluster")
        meta = MySQLDBMeta(
            ticket_data=self._ticket_data(TicketType.MYSQL_ROLLBACK_EXERCISE),
            cluster=self._cluster(),
        )
        with patch(CREATE_PATH), patch(GET_CLUSTER_PATH, return_value=cluster_row) as get_cluster, patch(
            GET_TAG_PATH, return_value=(exercise_tag, True)
        ) as get_builtin_tag:
            result = meta.mysql_single_apply(builtin_cluster_tags=(SystemTagEnum.EXERCISE,))

        self.assertTrue(result)
        get_builtin_tag.assert_called_once_with(key=SystemTagEnum.EXERCISE, value=True, type=TagType.CLUSTER)
        called = get_builtin_tag.call_args.kwargs
        self.assertEqual(called["key"], "exercise")
        self.assertIs(called["value"], True)
        self.assertEqual(called["type"], "cluster")
        self.assertEqual(
            [item.kwargs for item in get_cluster.call_args_list],
            [
                {"bk_biz_id": 3, "immute_domain": "rb-exercise-a.db"},
                {"bk_biz_id": 3, "immute_domain": "rb-exercise-b.db"},
            ],
        )
        self.assertEqual(cluster_row.tags.add.call_count, 2)
        for add_call in cluster_row.tags.add.call_args_list:
            self.assertEqual(add_call.args, (exercise_tag,))

    def test_single_apply_attaches_each_builtin_tag_key(self):
        exercise_tag = MagicMock(name="exercise_tag")
        temporary_tag = MagicMock(name="temporary_tag")
        cluster_row = MagicMock(name="cluster")
        meta = MySQLDBMeta(
            ticket_data=self._ticket_data(TicketType.MYSQL_ROLLBACK_EXERCISE),
            cluster=self._cluster(),
        )
        with patch(CREATE_PATH), patch(GET_CLUSTER_PATH, return_value=cluster_row), patch(
            GET_TAG_PATH, side_effect=[(exercise_tag, True), (temporary_tag, True)]
        ) as get_builtin_tag:
            result = meta.mysql_single_apply(
                builtin_cluster_tags=(SystemTagEnum.EXERCISE, SystemTagEnum.TEMPORARY),
            )

        self.assertTrue(result)
        self.assertEqual(
            [item.kwargs["key"] for item in get_builtin_tag.call_args_list],
            [SystemTagEnum.EXERCISE, SystemTagEnum.TEMPORARY],
        )
        self.assertEqual(
            [item.args for item in cluster_row.tags.add.call_args_list],
            [(exercise_tag,), (exercise_tag,), (temporary_tag,), (temporary_tag,)],
        )

    def test_single_apply_does_not_attach_tag(self):
        meta = MySQLDBMeta(
            ticket_data=self._ticket_data(TicketType.MYSQL_ROLLBACK_EXERCISE),
            cluster=self._cluster(),
        )
        with patch(CREATE_PATH), patch(GET_TAG_PATH) as get_builtin_tag:
            result = meta.mysql_single_apply()

        self.assertTrue(result)
        get_builtin_tag.assert_not_called()
