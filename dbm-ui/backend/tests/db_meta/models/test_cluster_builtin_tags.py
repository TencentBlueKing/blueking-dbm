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
from django.test import TestCase

from backend.db_meta.enums import ClusterType
from backend.db_meta.enums.comm import SystemTagEnum, TagType
from backend.db_meta.models import Tag
from backend.db_meta.models.cluster import Cluster


class TestClusterBuiltinTagFilter(TestCase):
    def _cluster(self, name):
        return Cluster.objects.create(
            bk_biz_id=3,
            cluster_type=ClusterType.TenDBHA.value,
            name=name,
            immute_domain="{}.db".format(name),
        )

    def _tag(self, key, is_builtin):
        return Tag.objects.create(
            bk_biz_id=0,
            key=key,
            value="True",
            type=TagType.CLUSTER,
            is_builtin=is_builtin,
        )

    def test_exclude_and_filter_split_builtin_cluster_tags(self):
        plain = self._cluster("plain-ha")
        temporary = self._cluster("temporary-ha")
        exercise = self._cluster("exercise-ha")
        custom_same_key = self._cluster("custom-temporary-ha")
        temporary.tags.add(self._tag(SystemTagEnum.TEMPORARY, True))
        exercise.tags.add(self._tag(SystemTagEnum.EXERCISE, True))
        custom_same_key.tags.add(
            Tag.objects.create(
                bk_biz_id=3,
                key=SystemTagEnum.TEMPORARY,
                value="True",
                type=TagType.CLUSTER,
                is_builtin=False,
            )
        )

        scoped = Cluster.objects.filter(bk_biz_id=3)
        excluded_ids = set(scoped.exclude_builtin_cluster_tags().values_list("id", flat=True))
        filtered_ids = set(scoped.filter_builtin_cluster_tags().values_list("id", flat=True))

        self.assertIn(plain.id, excluded_ids)
        self.assertIn(custom_same_key.id, excluded_ids)
        self.assertNotIn(temporary.id, excluded_ids)
        self.assertNotIn(exercise.id, excluded_ids)
        self.assertEqual(filtered_ids, {temporary.id, exercise.id})
