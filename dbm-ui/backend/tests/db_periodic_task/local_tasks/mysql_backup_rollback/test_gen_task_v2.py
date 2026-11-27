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
import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from backend.db_meta.enums import ClusterPhase, ClusterStatus, ClusterType
from backend.db_meta.models.cluster import Cluster
from backend.db_periodic_task.models import MySQLBackupRecoverTask, TaskPhase, TaskStatus
from backend.ticket.constants import ResourceApplyErrCode


def _v2():
    # 延迟导入，避免 pytest 收集阶段触发 local_tasks 注册并访问数据库
    from backend.db_periodic_task.local_tasks.mysql_backup_rollback import gen_task_v2

    return gen_task_v2


def _make_host(
    host_id: int,
    ip: str,
    mount_sizes: dict,
    os_name: str = "tlinux-2.6",
    bk_cloud_id: int = 0,
    bk_biz_id: int = 2005000002,
):
    return _v2().FreeHost(
        bk_host_id=host_id,
        ip=ip,
        bk_cloud_id=bk_cloud_id,
        bk_biz_id=bk_biz_id,
        os_type="Linux",
        os_name=os_name,
        mount_sizes=mount_sizes,
        labels=["1"],
    )


def _make_cluster_stub(
    cluster_id: int,
    bk_biz_id: int,
    cluster_type: str = ClusterType.TenDBHA.value,
    domain: str = "",
):
    return SimpleNamespace(
        id=cluster_id,
        bk_biz_id=bk_biz_id,
        cluster_type=cluster_type,
        immute_domain=domain or f"c{cluster_id}.test.db",
    )


def _make_candidate(
    cluster_id: int,
    bk_biz_id: int,
    storage_spec: list,
    tier: int = 1,
    cluster_type: str = ClusterType.TenDBHA.value,
    mysql_version: str = "5.7.20-tmysql-3.4.2",
    recover_success_cnt: int = 0,
):
    v2 = _v2()
    cluster = _make_cluster_stub(cluster_id, bk_biz_id, cluster_type=cluster_type)
    required_disk_gb = sum(int(s.get("min", 0) or 0) for s in storage_spec)
    now_iso = timezone.now().isoformat()
    backup_id = f"bkp-{cluster_id}"
    extra_fields = {
        "bk_cloud_id": 0,
        "encrypt_enable": False,
        "time_zone": "+08:00",
        "backup_charset": "utf8mb4",
        "backup_tool": "xtrabackup",
        "sql_mode": "",
        "data_dir_size_mb": required_disk_gb * 1024,
        "storage_engine": "innodb",
    }
    backup_record = {
        "bk_biz_id": bk_biz_id,
        "cluster_id": cluster_id,
        "cluster_address": cluster.immute_domain,
        "backup_id": backup_id,
        "backup_consistent_time": now_iso,
        "backup_begin_time": now_iso,
        "backup_end_time": now_iso,
        "total_filesize": required_disk_gb * 1024 * 1024 * 1024,
        "backup_host": "127.0.0.10",
        "mysql_role": "slave",
        "backup_type": "physical",
        "mysql_version": mysql_version,
        "binlog_info": json.dumps({}),
        "file_list": json.dumps([]),
        "extra_fields": json.dumps(extra_fields),
        "backup_source": "remote",
    }
    return v2.ExerciseCandidate(
        cluster=cluster,
        tier=tier,
        recover_success_cnt=recover_success_cnt,
        backup_record=backup_record,
        parsed_extra_fields=extra_fields,
        storage_spec=storage_spec,
        mysql_version=mysql_version,
        need_mysql8=v2._is_mysql8_or_above(mysql_version),
        required_disk_gb=required_disk_gb,
        backup_id=backup_id,
        backup_file_size_gb=float(required_disk_gb),
    )


class TestHostCanFit(TestCase):
    def test_dual_disk_and_single_disk_matching(self):
        v2 = _v2()
        dual_host = _make_host(1, "127.0.0.1", {"/data": 200, "/data1": 2000})
        single_host = _make_host(2, "127.0.0.2", {"/data": 500})

        dual_spec = [
            {"mount_point": "/data", "min": 100, "max": 2147483647},
            {"mount_point": "/data1", "min": 1500, "max": 2147483647},
        ]
        small_single_spec = [{"min": 200, "max": 2147483647}]
        huge_single_spec = [{"min": 3000, "max": 2147483647}]

        self.assertTrue(v2.host_can_fit(dual_host, dual_spec, "5.7.20"))
        self.assertFalse(v2.host_can_fit(single_host, dual_spec, "5.7.20"))
        self.assertTrue(v2.host_can_fit(single_host, small_single_spec, "5.7.20"))
        self.assertTrue(v2.host_can_fit(dual_host, small_single_spec, "5.7.20"))
        self.assertFalse(v2.host_can_fit(dual_host, huge_single_spec, "5.7.20"))

    def test_mysql8_excludes_tlinux12_and_empty_os(self):
        v2 = _v2()
        old_os_host = _make_host(1, "127.0.0.1", {"/data": 500}, os_name="tlinux-1.2")
        empty_os_host = _make_host(2, "127.0.0.2", {"/data": 500}, os_name="")
        new_os_host = _make_host(3, "127.0.0.3", {"/data": 500}, os_name="tlinux-2.6")
        spec = [{"min": 200, "max": 2147483647}]

        self.assertFalse(v2.host_can_fit(old_os_host, spec, "8.0.32"))
        self.assertFalse(v2.host_can_fit(empty_os_host, spec, "8.0.32"))
        self.assertTrue(v2.host_can_fit(new_os_host, spec, "8.0.32"))
        self.assertTrue(v2.host_can_fit(old_os_host, spec, "5.7.20"))


class TestTypeQuotaRatio(TestCase):
    def test_negative_feedback_aligned_with_cluster_ratio(self):
        v2 = _v2()
        # 存量 20% TenDBCluster / 80% TenDBHA，近24h也正好 20% / 80%，不应被拉偏到 50%/50%
        targets = v2.calculate_cluster_type_targets(
            total_hosts=10,
            recent_stats={"tendbcluster_count": 20, "tendbha_count": 80, "total_count": 100},
            tendbcluster_count=200,
            tendbha_count=800,
        )
        self.assertEqual(targets[ClusterType.TenDBCluster.value], 2)
        self.assertEqual(targets[ClusterType.TenDBHA.value], 8)


class TestMatchingStrategy(TestCase):
    def test_large_backup_gets_large_host_within_same_tier(self):
        v2 = _v2()
        large_host = _make_host(101, "127.0.0.11", {"/data": 200, "/data1": 4000})
        small_host_1 = _make_host(102, "127.0.0.12", {"/data": 500})
        small_host_2 = _make_host(103, "127.0.0.13", {"/data": 500})
        remaining_hosts = [large_host, small_host_1, small_host_2]

        small_spec = [{"min": 200, "max": 2147483647}]
        large_spec = [
            {"mount_point": "/data", "min": 100, "max": 2147483647},
            {"mount_point": "/data1", "min": 2000, "max": 2147483647},
        ]
        # 小备份排在列表前面，大备份排在后面，验证大备份不会被小备份挤掉
        candidates = [
            _make_candidate(1, 1001, small_spec, tier=1),
            _make_candidate(2, 1002, small_spec, tier=1),
            _make_candidate(3, 1003, small_spec, tier=1),
            _make_candidate(4, 1004, large_spec, tier=1),
        ]
        type_quota = {ClusterType.TenDBCluster.value: 0, ClusterType.TenDBHA.value: 3}
        biz_used = {1001: 0, 1002: 0, 1003: 0, 1004: 0}
        from collections import defaultdict

        assignments = v2.match_candidates_to_hosts(
            candidates=candidates,
            remaining_hosts=remaining_hosts,
            type_quota=type_quota,
            biz_used=defaultdict(int, biz_used),
            tier=1,
        )
        self.assertEqual(len(assignments), 3)
        self.assertEqual(len(remaining_hosts), 0)
        assigned_map = {cand.cluster.id: host.bk_host_id for cand, host in assignments}
        # 大备份(4)必须拿到大机(101)
        self.assertEqual(assigned_map[4], 101)

    def test_tier1_small_uses_small_host_leaving_large_host_for_tier2_large(self):
        v2 = _v2()
        large_host = _make_host(201, "127.0.0.21", {"/data": 200, "/data1": 4000})
        small_host = _make_host(202, "127.0.0.22", {"/data": 500})

        tier1_cluster = _make_cluster_stub(10, 2001)
        tier2_small = _make_cluster_stub(20, 3001)
        tier2_large = _make_cluster_stub(21, 3002)

        spec_by_cid = {
            10: [{"min": 200, "max": 2147483647}],
            20: [{"min": 200, "max": 2147483647}],
            21: [
                {"mount_point": "/data", "min": 100, "max": 2147483647},
                {"mount_point": "/data1", "min": 2000, "max": 2147483647},
            ],
        }
        cand_map = {
            10: _make_candidate(10, 2001, spec_by_cid[10], tier=1),
            20: _make_candidate(20, 3001, spec_by_cid[20], tier=2),
            21: _make_candidate(21, 3002, spec_by_cid[21], tier=2),
        }

        def fake_find_backup(cluster, start_time, end_time, exercised_backup_ids):
            return MagicMock(backup_id=f"bkp-{cluster.id}")

        def fake_build_cand(cluster, backup_result, tier, recover_success_cnt):
            return cand_map[cluster.id]

        cache.clear()
        now = timezone.now()
        with patch.object(v2, "_find_latest_usable_backup", side_effect=fake_find_backup), patch.object(
            v2, "_build_candidate_from_backup", side_effect=fake_build_cand
        ):
            assignments, unassigned, unused_stats = v2.plan_exercise_assignments(
                free_hosts=[large_host, small_host],
                tier1_stream=[tier1_cluster],
                tier2_stream=[tier2_small, tier2_large],
                type_targets={ClusterType.TenDBCluster.value: 0, ClusterType.TenDBHA.value: 2},
                start_time=now - timedelta(days=7),
                end_time=now - timedelta(days=1),
                exercised_backup_ids=set(),
                recover_success_map={},
            )

        self.assertEqual(len(unassigned), 0)
        assigned_map = {cand.cluster.id: host.bk_host_id for cand, host in assignments}
        # Tier1 小集群走 Best-Fit 用小机(202)，大机(201)留给 Tier2 大备份(21)
        self.assertEqual(assigned_map, {10: 202, 21: 201})

    def test_tier1_strictly_preempts_tier2_even_on_large_host(self):
        v2 = _v2()
        large_host = _make_host(301, "127.0.0.31", {"/data": 200, "/data1": 4000})
        small_host = _make_host(302, "127.0.0.32", {"/data": 500})

        t1_a = _make_cluster_stub(11, 2001)
        t1_b = _make_cluster_stub(12, 2002)
        t2_large = _make_cluster_stub(22, 3001)

        cand_map = {
            11: _make_candidate(11, 2001, [{"min": 200, "max": 2147483647}], tier=1),
            12: _make_candidate(12, 2002, [{"min": 200, "max": 2147483647}], tier=1),
            22: _make_candidate(
                22,
                3001,
                [
                    {"mount_point": "/data", "min": 100, "max": 2147483647},
                    {"mount_point": "/data1", "min": 2000, "max": 2147483647},
                ],
                tier=2,
            ),
        }

        cache.clear()
        now = timezone.now()
        with patch.object(
            v2, "_find_latest_usable_backup", side_effect=lambda c, *a: MagicMock(backup_id=f"bkp-{c.id}")
        ), patch.object(v2, "_build_candidate_from_backup", side_effect=lambda cluster, **kw: cand_map[cluster.id]):
            assignments, unassigned, unused_stats = v2.plan_exercise_assignments(
                free_hosts=[large_host, small_host],
                tier1_stream=[t1_a, t1_b],
                tier2_stream=[t2_large],
                type_targets={ClusterType.TenDBCluster.value: 0, ClusterType.TenDBHA.value: 2},
                start_time=now - timedelta(days=7),
                end_time=now - timedelta(days=1),
                exercised_backup_ids=set(),
                recover_success_map={},
            )

        self.assertEqual(len(unassigned), 0)
        selected_cids = {cand.cluster.id for cand, unused_host in assignments}
        # 未演练业务最优先：2 台机器全给 Tier1，大机自动降级不空跑
        self.assertEqual(selected_cids, {11, 12})

    def test_single_large_host_still_prefers_large_backup_within_same_tier(self):
        v2 = _v2()
        large_host = _make_host(351, "127.0.0.35", {"/data": 200, "/data1": 4000})
        t1_small = _make_cluster_stub(15, 2001)
        t1_large = _make_cluster_stub(16, 2002)

        cand_map = {
            15: _make_candidate(15, 2001, [{"min": 200, "max": 2147483647}], tier=1),
            16: _make_candidate(
                16,
                2002,
                [
                    {"mount_point": "/data", "min": 100, "max": 2147483647},
                    {"mount_point": "/data1", "min": 2000, "max": 2147483647},
                ],
                tier=1,
            ),
        }

        cache.clear()
        now = timezone.now()
        with patch.object(
            v2, "_find_latest_usable_backup", side_effect=lambda c, *a: MagicMock(backup_id=f"bkp-{c.id}")
        ), patch.object(v2, "_build_candidate_from_backup", side_effect=lambda cluster, **kw: cand_map[cluster.id]):
            assignments, unassigned, unused_stats = v2.plan_exercise_assignments(
                free_hosts=[large_host],
                tier1_stream=[t1_small, t1_large],
                tier2_stream=[],
                type_targets={ClusterType.TenDBCluster.value: 0, ClusterType.TenDBHA.value: 1},
                start_time=now - timedelta(days=7),
                end_time=now - timedelta(days=1),
                exercised_backup_ids=set(),
                recover_success_map={},
            )

        self.assertEqual(len(unassigned), 0)
        self.assertEqual([(c.cluster.id, h.bk_host_id) for c, h in assignments], [(16, 351)])


class TestSpecCacheAndNoEmptyRun(TestCase):
    def test_unfit_high_priority_clusters_skipped_cached_and_auto_released(self):
        v2 = _v2()
        small_host = _make_host(401, "127.0.0.41", {"/data": 500})
        large_host = _make_host(402, "127.0.0.42", {"/data": 200, "/data1": 4000})

        huge_cluster = _make_cluster_stub(50, 5001)
        small_cluster = _make_cluster_stub(51, 5002)

        huge_spec = [
            {"mount_point": "/data", "min": 100, "max": 2147483647},
            {"mount_point": "/data1", "min": 3000, "max": 2147483647},
        ]
        small_spec = [{"min": 200, "max": 2147483647}]
        cand_map = {
            50: _make_candidate(50, 5001, huge_spec, tier=1),
            51: _make_candidate(51, 5002, small_spec, tier=1),
        }

        cache.clear()
        now = timezone.now()

        # 第 1 轮：只有小机 -> 高优大集群(50)跳过并写缓存，同轮顺利调度小集群(51)，零空调度
        with patch.object(
            v2, "_find_latest_usable_backup", side_effect=lambda c, *a: MagicMock(backup_id=f"bkp-{c.id}")
        ) as find_mock, patch.object(
            v2, "_build_candidate_from_backup", side_effect=lambda cluster, **kw: cand_map[cluster.id]
        ):
            assignments_1, unassigned_1, stats_1 = v2.plan_exercise_assignments(
                free_hosts=[small_host],
                tier1_stream=[huge_cluster, small_cluster],
                tier2_stream=[],
                type_targets={ClusterType.TenDBCluster.value: 0, ClusterType.TenDBHA.value: 1},
                start_time=now - timedelta(days=7),
                end_time=now - timedelta(days=1),
                exercised_backup_ids=set(),
                recover_success_map={},
            )
            self.assertEqual(len(unassigned_1), 0)
            self.assertEqual([c.cluster.id for c, unused_h in assignments_1], [51])
            self.assertEqual(stats_1["skipped_spec_mismatch"], 1)
            self.assertEqual(find_mock.call_count, 2)

        # 第 2 轮：仍只有小机 -> 大集群(50)命中 Redis 需求缓存，0 次 DB 查询直接跳过
        with patch.object(
            v2, "_find_latest_usable_backup", side_effect=lambda c, *a: MagicMock(backup_id=f"bkp-{c.id}")
        ) as find_mock_2, patch.object(
            v2, "_build_candidate_from_backup", side_effect=lambda cluster, **kw: cand_map[cluster.id]
        ):
            assignments_2, unused_u2, stats_2 = v2.plan_exercise_assignments(
                free_hosts=[small_host],
                tier1_stream=[huge_cluster, small_cluster],
                tier2_stream=[],
                type_targets={ClusterType.TenDBCluster.value: 0, ClusterType.TenDBHA.value: 1},
                start_time=now - timedelta(days=7),
                end_time=now - timedelta(days=1),
                exercised_backup_ids=set(),
                recover_success_map={},
            )
            self.assertEqual([c.cluster.id for c, unused_h in assignments_2], [51])
            self.assertEqual(stats_2["skipped_by_spec_cache"], 1)
            self.assertEqual(find_mock_2.call_count, 1)

        # 第 3 轮：新进一台 4TB 双盘大机 -> 缓存校验通过自动放行，大集群(50)立刻被调度！
        with patch.object(
            v2, "_find_latest_usable_backup", side_effect=lambda c, *a: MagicMock(backup_id=f"bkp-{c.id}")
        ), patch.object(v2, "_build_candidate_from_backup", side_effect=lambda cluster, **kw: cand_map[cluster.id]):
            assignments_3, unassigned_3, stats_3 = v2.plan_exercise_assignments(
                free_hosts=[large_host],
                tier1_stream=[huge_cluster, small_cluster],
                tier2_stream=[],
                type_targets={ClusterType.TenDBCluster.value: 0, ClusterType.TenDBHA.value: 1},
                start_time=now - timedelta(days=7),
                end_time=now - timedelta(days=1),
                exercised_backup_ids=set(),
                recover_success_map={},
            )
            self.assertEqual(len(unassigned_3), 0)
            self.assertEqual(stats_3["skipped_by_spec_cache"], 0)
            self.assertEqual([(c.cluster.id, h.bk_host_id) for c, h in assignments_3], [(50, 402)])


class TestClusterFilteringAndTargetedApply(TestCase):
    def test_excludes_offline_and_temporary_clusters(self):
        v2 = _v2()
        online = Cluster.objects.create(
            bk_biz_id=6001,
            cluster_type=ClusterType.TenDBHA.value,
            immute_domain="online.v2.exercise.db",
            name="online",
            phase=ClusterPhase.ONLINE.value,
            status=ClusterStatus.NORMAL.value,
        )
        offline = Cluster.objects.create(
            bk_biz_id=6001,
            cluster_type=ClusterType.TenDBHA.value,
            immute_domain="offline.v2.exercise.db",
            name="offline",
            phase=ClusterPhase.OFFLINE.value,
            status=ClusterStatus.NORMAL.value,
        )
        temp = Cluster.objects.create(
            bk_biz_id=6001,
            cluster_type=ClusterType.TenDBHA.value,
            immute_domain="temp.v2.exercise.db",
            name="temp",
            phase=ClusterPhase.ONLINE.value,
            status=ClusterStatus.TEMPORARY.value,
        )

        ids = set(
            v2._base_online_clusters_queryset()
            .filter(id__in=[online.id, offline.id, temp.id])
            .values_list("id", flat=True)
        )
        self.assertEqual(ids, {online.id})

    def test_targeted_apply_fallback_on_resource_lake(self):
        v2 = _v2()
        primary_host = _make_host(701, "127.0.0.71", {"/data": 500})
        fallback_host = _make_host(702, "127.0.0.72", {"/data": 600})
        candidate = _make_candidate(70, 7001, [{"min": 200, "max": 2147483647}], mysql_version="8.0.32")
        backup_hosts = [fallback_host]

        apply_calls = []

        def fake_apply(params, raw=True):
            apply_calls.append(params)
            if len(apply_calls) == 1:
                return {"code": ResourceApplyErrCode.RESOURCE_LAKE, "message": "busy"}
            return {
                "code": 0,
                "request_id": "req-1",
                "data": [
                    {
                        "data": [
                            {
                                "ip": fallback_host.ip,
                                "bk_host_id": fallback_host.bk_host_id,
                                "bk_cloud_id": fallback_host.bk_cloud_id,
                                "bk_biz_id": fallback_host.bk_biz_id,
                                "labels": fallback_host.labels,
                            }
                        ]
                    }
                ],
            }

        with patch.object(v2.DBResourceApi, "resource_apply", side_effect=fake_apply), patch.object(
            v2, "MySQLRollbackExerciseFlow"
        ) as flow_cls:
            ok = v2._submit_exercise_task(candidate, primary_host, backup_hosts)

        self.assertTrue(ok)
        self.assertEqual(len(apply_calls), 2)
        self.assertEqual(apply_calls[0]["details"][0]["hosts"][0]["bk_host_id"], 701)
        self.assertEqual(apply_calls[1]["details"][0]["hosts"][0]["bk_host_id"], 702)
        self.assertTrue(apply_calls[0]["details"][0]["exclude_os_name"])
        flow_cls.return_value.run.assert_called_once()
        task_row = MySQLBackupRecoverTask.objects.get(cluster_id=70)
        self.assertEqual(task_row.task_status, TaskStatus.COMMIT_SUCCESS)
        self.assertEqual(task_row.exercise_host_ip, "127.0.0.72")
        self.assertEqual(task_row.phase, TaskPhase.RUNNING)

    def test_fetch_free_hosts_requests_unused_status_and_filters_non_unused(self):
        v2 = _v2()
        captured_params = {}

        def fake_list(params, raw=True):
            captured_params.update(params)
            return {
                "code": 0,
                "data": {
                    "details": [
                        {
                            "bk_host_id": 801,
                            "ip": "127.0.0.81",
                            "bk_cloud_id": 0,
                            "bk_biz_id": 2005000002,
                            "os_type": "Linux",
                            "os_name": "tlinux-2.6",
                            "status": "Unused",
                            "labels": ["1"],
                            "storage_device": {
                                "/data": {"size": "200.5", "disk_type": "SSD"},
                                "/data1": {"size": "invalid", "disk_type": "HDD"},
                            },
                        },
                        {
                            "bk_host_id": 802,
                            "ip": "127.0.0.82",
                            "os_type": "Linux",
                            "os_name": "tlinux-2.6",
                            "status": "Prepoccupied",
                            "storage_device": {"/data": {"size": 500}},
                        },
                        {
                            "bk_host_id": 803,
                            "ip": "127.0.0.83",
                            "os_type": "Windows",
                            "status": "Unused",
                            "storage_device": {"/data": {"size": 500}},
                        },
                    ]
                },
            }

        with patch.object(v2.DBResourceApi, "resource_list", side_effect=fake_list):
            hosts = v2.fetch_free_hosts()

        self.assertEqual(captured_params.get("status"), ["Unused"])
        self.assertEqual([h.bk_host_id for h in hosts], [801])
        self.assertEqual(hosts[0].mount_sizes, {"/data": 200})
        self.assertEqual(hosts[0].mount_disk_types, {"/data": "SSD"})

    def test_host_can_fit_checks_optional_disk_type(self):
        v2 = _v2()
        host = v2.FreeHost(
            bk_host_id=811,
            ip="127.0.0.84",
            bk_cloud_id=0,
            bk_biz_id=2005000002,
            os_type="Linux",
            os_name="tlinux-2.6",
            mount_sizes={"/data": 300, "/data1": 1000},
            mount_disk_types={"/data": "HDD", "/data1": "SSD"},
        )
        self.assertTrue(
            v2.host_can_fit(host, [{"mount_point": "/data1", "disk_type": "SSD", "min": 500, "max": 0}], "5.7.20")
        )
        self.assertFalse(
            v2.host_can_fit(host, [{"mount_point": "/data1", "disk_type": "HDD", "min": 500, "max": 0}], "5.7.20")
        )
        self.assertTrue(v2.host_can_fit(host, [{"disk_type": "SSD", "min": 800, "max": 0}], "5.7.20"))
        self.assertFalse(v2.host_can_fit(host, [{"disk_type": "HDD", "min": 800, "max": 0}], "5.7.20"))

    def test_tier2_heavy_prefers_lower_recover_success_count_over_max_size(self):
        v2 = _v2()
        large_host = _make_host(821, "127.0.0.85", {"/data": 4000})
        small_host = _make_host(822, "127.0.0.86", {"/data": 400})
        frequent_huge = _make_candidate(8210, 8201, [{"min": 2000, "max": 2147483647}], tier=2, recover_success_cnt=30)
        rare_large = _make_candidate(8211, 8202, [{"min": 1200, "max": 2147483647}], tier=2, recover_success_cnt=0)
        small_cand = _make_candidate(8212, 8203, [{"min": 100, "max": 2147483647}], tier=2, recover_success_cnt=0)

        remaining = [large_host, small_host]
        matched = v2.match_candidates_to_hosts(
            candidates=[frequent_huge, rare_large, small_cand],
            remaining_hosts=remaining,
            type_quota={ClusterType.TenDBCluster.value: 0, ClusterType.TenDBHA.value: 2},
            biz_used=v2.defaultdict(int),
            tier=2,
            all_hosts=[large_host, small_host],
        )
        by_host = {h.bk_host_id: c.cluster.id for c, h in matched}
        self.assertEqual(by_host[821], 8211)
        self.assertEqual(by_host[822], 8212)

    def test_deferred_pool_avoids_early_relaxation_across_batches(self):
        v2 = _v2()
        cache.clear()
        hosts = [_make_host(831, "127.0.0.87", {"/data": 400}), _make_host(832, "127.0.0.88", {"/data": 400})]
        # 前 8 个均来自同一业务 8301（模拟第 1 批收集），第 9 个来自另一未演练业务 8302（第 2 批）
        biz1_clusters = [_make_cluster_stub(8300 + i, 8301) for i in range(1, 9)]
        biz2_cluster = _make_cluster_stub(8399, 8302)
        stream = biz1_clusters + [biz2_cluster]
        cand_map = {
            c.id: _make_candidate(c.id, c.bk_biz_id, [{"min": 100, "max": 2147483647}], tier=1) for c in stream
        }
        now = timezone.now()

        with patch.object(v2, "_find_latest_usable_backup", side_effect=lambda c, *a, **k: MagicMock()), patch.object(
            v2, "_build_candidate_from_backup", side_effect=lambda cluster, **k: cand_map[cluster.id]
        ):
            assignments, remaining, unused_stats = v2.plan_exercise_assignments(
                free_hosts=hosts,
                tier1_stream=stream,
                tier2_stream=[],
                type_targets={ClusterType.TenDBCluster.value: 0, ClusterType.TenDBHA.value: 2},
                start_time=now - timedelta(days=7),
                end_time=now - timedelta(days=1),
                exercised_backup_ids=set(),
                recover_success_map={},
            )

        self.assertEqual(len(remaining), 0)
        picked_bizs = {c.cluster.bk_biz_id for c, _h in assignments}
        self.assertEqual(picked_bizs, {8301, 8302})

    def test_no_backup_cache_skips_repeat_db_queries_and_preserves_tier2_budget(self):
        v2 = _v2()
        cache.clear()
        host = _make_host(841, "127.0.0.89", {"/data": 400})
        no_bkp_cluster = _make_cluster_stub(8401, 8401)
        tier2_cluster = _make_cluster_stub(8402, 8402)
        tier2_cand = _make_candidate(8402, 8402, [{"min": 100, "max": 2147483647}], tier=2)
        now = timezone.now()

        def fake_find(cluster, *args, **kwargs):
            return None if cluster.id == 8401 else MagicMock()

        # 第 1 轮：8401 查库无备份 -> 写无备份负缓存，8402 补位
        with patch.object(v2, "_find_latest_usable_backup", side_effect=fake_find), patch.object(
            v2, "_build_candidate_from_backup", return_value=tier2_cand
        ):
            assign1, rem1, stats1 = v2.plan_exercise_assignments(
                free_hosts=[host],
                tier1_stream=[no_bkp_cluster],
                tier2_stream=[tier2_cluster],
                type_targets={ClusterType.TenDBCluster.value: 0, ClusterType.TenDBHA.value: 1},
                start_time=now - timedelta(days=7),
                end_time=now - timedelta(days=1),
                exercised_backup_ids=set(),
                recover_success_map={},
            )
        self.assertEqual(len(rem1), 0)
        self.assertEqual(assign1[0][0].cluster.id, 8402)
        self.assertEqual(stats1["no_backup"], 1)

        # 第 2 轮：8401 命中无备份负缓存（0 次 DB 查询）直接跳过
        checked = []

        def fake_find_round2(cluster, *args, **kwargs):
            checked.append(cluster.id)
            return MagicMock()

        with patch.object(v2, "_find_latest_usable_backup", side_effect=fake_find_round2), patch.object(
            v2, "_build_candidate_from_backup", return_value=tier2_cand
        ):
            assign2, rem2, stats2 = v2.plan_exercise_assignments(
                free_hosts=[host],
                tier1_stream=[no_bkp_cluster],
                tier2_stream=[tier2_cluster],
                type_targets={ClusterType.TenDBCluster.value: 0, ClusterType.TenDBHA.value: 1},
                start_time=now - timedelta(days=7),
                end_time=now - timedelta(days=1),
                exercised_backup_ids=set(),
                recover_success_map={},
            )
        self.assertEqual(len(rem2), 0)
        self.assertEqual(checked, [8402])
        self.assertEqual(stats2["skipped_by_no_backup_cache"], 1)
        self.assertEqual(assign2[0][0].cluster.id, 8402)

    def test_submit_returns_host_when_task_save_fails_and_batch_isolates_exception(self):
        v2 = _v2()
        host1 = _make_host(851, "127.0.0.91", {"/data": 500})
        host2 = _make_host(852, "127.0.0.92", {"/data": 500})
        cand1 = _make_candidate(8501, 8501, [{"min": 100, "max": 2147483647}])
        cand2 = _make_candidate(8502, 8502, [{"min": 100, "max": 2147483647}])

        apply_resp_1 = {
            "code": 0,
            "request_id": "req-save-fail",
            "data": [
                {
                    "data": [
                        {
                            "ip": host1.ip,
                            "bk_host_id": host1.bk_host_id,
                            "bk_cloud_id": host1.bk_cloud_id,
                            "bk_biz_id": host1.bk_biz_id,
                            "labels": host1.labels,
                        }
                    ]
                }
            ],
        }

        # 1) task.save() 失败时必须归还已申请的主机，避免主机泄露
        with patch.object(v2.DBResourceApi, "resource_apply", return_value=apply_resp_1), patch.object(
            MySQLBackupRecoverTask, "save", side_effect=RuntimeError("db write failed")
        ), patch.object(v2, "return_resource") as mock_return:
            ok = v2._submit_exercise_task(cand1, host1, [])

        self.assertFalse(ok)
        mock_return.assert_called_once()
        returned_host = mock_return.call_args[0][0]["hosts"][0]
        self.assertEqual(returned_host["ip"], "127.0.0.91")

        # 2) gen_rollback_task_v2 端到端串联：第 1 个任务抛网络异常不中断第 2 个任务提交
        def fake_apply_batch(params, raw=True):
            host_id = params["details"][0]["hosts"][0]["bk_host_id"]
            if host_id == 851:
                raise RuntimeError("network timeout")
            return {
                "code": 0,
                "request_id": "req-ok-2",
                "data": [
                    {
                        "data": [
                            {
                                "ip": host2.ip,
                                "bk_host_id": host2.bk_host_id,
                                "bk_cloud_id": host2.bk_cloud_id,
                                "bk_biz_id": host2.bk_biz_id,
                                "labels": host2.labels,
                            }
                        ]
                    }
                ],
            }

        stats = {
            "skipped_by_no_backup_cache": 0,
            "skipped_by_spec_cache": 0,
            "backup_db_checked": 2,
            "no_backup": 0,
            "skipped_spec_mismatch": 0,
            "skipped_no_remaining_fit": 0,
        }
        with patch.object(v2, "fetch_free_hosts", return_value=[host1, host2]), patch.object(
            v2, "load_exercised_backup_ids", return_value=set()
        ), patch.object(v2, "prepare_tiered_cluster_streams", return_value=([], [], {}, {})), patch.object(
            v2, "plan_exercise_assignments", return_value=([(cand1, host1), (cand2, host2)], [], stats)
        ), patch.object(
            v2.DBResourceApi, "resource_apply", side_effect=fake_apply_batch
        ), patch.object(
            v2, "MySQLRollbackExerciseFlow"
        ) as flow_cls:
            v2.gen_rollback_task_v2()

        flow_cls.return_value.run.assert_called_once()
        task_row = MySQLBackupRecoverTask.objects.get(cluster_id=8502)
        self.assertEqual(task_row.exercise_host_ip, "127.0.0.92")
        self.assertEqual(task_row.task_status, TaskStatus.COMMIT_SUCCESS)


class TestNonDirectCloudCosIgnorePolicy(TestCase):
    def setUp(self):
        cache.clear()

    def test_has_valid_cos_config_rules(self):
        v2 = _v2()
        self.assertTrue(
            v2._has_valid_cos_config({"cos_auth": {"storage_type": "cos", "bucket_name": "dbm-backup-1250000001"}})
        )
        self.assertTrue(
            v2._has_valid_cos_config({"cos_auth": {"storage_type": "S3", "bucket_name": "s3-backup-bucket"}})
        )
        self.assertTrue(
            v2._has_valid_cos_config({"cos_auth": {"storage_type": "bkrepo", "bucket_name": "bkrepo-bucket"}})
        )
        self.assertFalse(
            v2._has_valid_cos_config({"cos_auth": {"storage_type": "cos", "bucket_name": "{{.CosAuth.BucketName}}"}})
        )
        self.assertFalse(v2._has_valid_cos_config({"cos_auth": {"storage_type": "cos", "bucket_name": ""}}))
        self.assertFalse(v2._has_valid_cos_config({"cos_auth": {"storage_type": "hdfs", "bucket_name": "bucket"}}))
        self.assertFalse(v2._has_valid_cos_config({"cos_auth": {"storage_type": "", "bucket_name": "bucket"}}))
        self.assertFalse(v2._has_valid_cos_config(None))

    def test_batch_check_cloud_cos_caches_24h_and_skips_cache_on_api_error(self):
        v2 = _v2()
        query_calls = []

        def fake_query(params):
            key = (int(params["bk_biz_id"]), int(params["level_value"]))
            query_calls.append(key)
            if key == (9001, 1):
                return {"content": {"cos_auth": {"storage_type": "cos", "bucket_name": "real-bucket-1"}}}
            if key == (9002, 2):
                return {"content": {"cos_auth": {"storage_type": "", "bucket_name": "{{.CosAuth.BucketName}}"}}}
            raise RuntimeError("dbconfig timeout")

        with patch.object(v2.DBConfigApi, "query_conf_item", side_effect=fake_query):
            first = v2._batch_check_cloud_cos_capability({(9001, 0), (9001, 1), (9002, 2), (9003, 3)})

        self.assertEqual(first, {(9001, 1): True, (9002, 2): False, (9003, 3): False})
        self.assertEqual(set(query_calls), {(9001, 1), (9002, 2), (9003, 3)})

        # 第二次调用：(9001, 1) 与 (9002, 2) 命中缓存不查 API，上次异常的 (9003, 3) 未写缓存可自动重试
        query_calls.clear()

        def fake_query_round2(params):
            key = (int(params["bk_biz_id"]), int(params["level_value"]))
            query_calls.append(key)
            return {"content": {"cos_auth": {"storage_type": "s3", "bucket_name": "recovered-bucket-3"}}}

        with patch.object(v2.DBConfigApi, "query_conf_item", side_effect=fake_query_round2):
            second = v2._batch_check_cloud_cos_capability({(9001, 1), (9002, 2), (9003, 3)})

        self.assertEqual(query_calls, [(9003, 3)])
        self.assertEqual(second, {(9001, 1): True, (9002, 2): False, (9003, 3): True})

    def test_prepare_streams_ignores_non_direct_cloud_without_cos(self):
        v2 = _v2()
        direct_c = Cluster.objects.create(
            bk_biz_id=9101,
            bk_cloud_id=0,
            cluster_type=ClusterType.TenDBHA.value,
            immute_domain="direct.cos.test.db",
            name="direct",
            phase=ClusterPhase.ONLINE.value,
            status=ClusterStatus.NORMAL.value,
        )
        with_cos_c = Cluster.objects.create(
            bk_biz_id=9102,
            bk_cloud_id=10,
            cluster_type=ClusterType.TenDBHA.value,
            immute_domain="withcos.cos.test.db",
            name="withcos",
            phase=ClusterPhase.ONLINE.value,
            status=ClusterStatus.NORMAL.value,
        )
        without_cos_c = Cluster.objects.create(
            bk_biz_id=9103,
            bk_cloud_id=20,
            cluster_type=ClusterType.TenDBCluster.value,
            immute_domain="nocos.cos.test.db",
            name="nocos",
            phase=ClusterPhase.ONLINE.value,
            status=ClusterStatus.NORMAL.value,
        )

        def fake_query(params):
            if params["bk_biz_id"] == "9102" and params["level_value"] == "10":
                return {"content": {"cos_auth": {"storage_type": "cos", "bucket_name": "biz9102-bucket"}}}
            return {"content": {"cos_auth": {"storage_type": "", "bucket_name": "{{.CosAuth.BucketName}}"}}}

        with patch.object(v2.DBConfigApi, "query_conf_item", side_effect=fake_query), patch.object(
            v2.ExerciseIgnoreConfig, "get_ignored_biz_ids", return_value=[]
        ), patch.object(v2.ExerciseIgnoreConfig, "get_ignored_cluster_ids", return_value=[]), patch.object(
            v2.MySQLBackupRecoverTask, "get_recent_2days_failed_cluster_ids", return_value=[]
        ), patch.object(
            v2.MySQLBackupRecoverTask, "get_running_task_cluster_ids", return_value=[]
        ), patch.object(
            v2.MySQLBackupRecoverTask, "get_today_task_cluster_ids", return_value=[]
        ), patch.object(
            v2.MySQLBackupRecoverTask, "get_all_practiced_biz_ids", return_value=[]
        ), patch.object(
            v2.MySQLBackupRecoverTask, "get_all_practiced_cluster_ids", return_value=[]
        ), patch.object(
            v2.MySQLBackupRecoverTask,
            "get_recent_24h_exercise_cluster_type_stats",
            return_value={"total_count": 0, "tendbcluster_count": 0, "tendbha_count": 0},
        ):
            tier1, tier2, type_targets, unused_map = v2.prepare_tiered_cluster_streams(total_hosts=2)

        all_ids = {c.id for c in tier1 + tier2}
        self.assertIn(direct_c.id, all_ids)
        self.assertIn(with_cos_c.id, all_ids)
        self.assertNotIn(without_cos_c.id, all_ids)
        # 唯一的 TenDBCluster 因无 COS 被排除后，软配额不应给 TenDBCluster 分配名额
        self.assertEqual(type_targets[ClusterType.TenDBCluster.value], 0)
        self.assertEqual(type_targets[ClusterType.TenDBHA.value], 2)


class TestExerciseHostSpecSnapshot(TestCase):
    def test_build_host_spec_snapshot_parses_dict_and_json_str(self):
        raw = {
            "ip": "127.0.0.10",
            "bk_host_id": 1001,
            "bk_cloud_id": 0,
            "device_class": "S5.4XLARGE32",
            "svr_type_name": "CVM",
            "cpu_num": 16,
            "dram_cap": 32768,
            "total_storage_cap": 1200,
            "total_data_storage_cap": 1000,
            "storage_device": '{"/data": {"size": 1000, "disk_type": "CLOUD_SSD"}}',
            "os_type": "Linux",
            "os_name": "tlinux-2.6",
            "city": "sz",
            "sub_zone": "gm",
            "idc_name": "idc-1",
            "rack_id": "rack-1",
            "status": "Used",
            "operator": "system",
        }
        snap = MySQLBackupRecoverTask.build_host_spec_snapshot(raw)
        self.assertEqual(snap["ip"], "127.0.0.10")
        self.assertEqual(snap["device_class"], "S5.4XLARGE32")
        self.assertEqual(snap["cpu_num"], 16)
        self.assertEqual(snap["dram_cap"], 32768)
        self.assertEqual(snap["storage_device"], {"/data": {"size": 1000, "disk_type": "CLOUD_SSD"}})
        self.assertNotIn("status", snap)
        self.assertNotIn("operator", snap)

        self.assertEqual(MySQLBackupRecoverTask.build_host_spec_snapshot(None), {})
        self.assertEqual(
            MySQLBackupRecoverTask.build_host_spec_snapshot({"ip": "127.0.0.11", "cpu_num": None}),
            {"ip": "127.0.0.11"},
        )

    def test_submit_exercise_task_persists_exercise_host_spec(self):
        v2 = _v2()
        cluster = Cluster.objects.create(
            bk_biz_id=9201,
            bk_cloud_id=0,
            cluster_type=ClusterType.TenDBHA.value,
            immute_domain="spec.test.db",
            name="spectest",
            phase=ClusterPhase.ONLINE.value,
            status=ClusterStatus.NORMAL.value,
        )
        host = v2.FreeHost(
            bk_host_id=921,
            ip="127.0.0.95",
            bk_cloud_id=0,
            bk_biz_id=2005000002,
            os_type="Linux",
            os_name="tlinux-2.6",
            mount_sizes={"/data": 500},
            labels=["1"],
        )
        cand = v2.ExerciseCandidate(
            cluster=cluster,
            tier=1,
            recover_success_cnt=0,
            backup_record={
                "bk_biz_id": cluster.bk_biz_id,
                "cluster_address": cluster.immute_domain,
                "backup_id": "bk-spec-1",
                "backup_begin_time": timezone.now() - timedelta(hours=2),
                "backup_end_time": timezone.now() - timedelta(hours=1),
                "backup_host": "127.0.0.1",
                "mysql_role": "slave",
                "backup_type": "physical",
                "binlog_info": "{}",
                "file_list": "[]",
                "extra_fields": "{}",
            },
            parsed_extra_fields={
                "backup_charset": "utf8mb4",
                "sql_mode": "",
                "backup_tool": "xtrabackup",
                "time_zone": "+08:00",
            },
            backup_id="bk-spec-1",
            backup_file_size_gb=50.0,
            mysql_version="MySQL-5.7",
            need_mysql8=False,
            storage_spec=[],
            required_disk_gb=150,
        )
        apply_resp = {
            "code": 0,
            "request_id": "req-spec-1",
            "data": [
                {
                    "data": [
                        {
                            "ip": host.ip,
                            "bk_host_id": host.bk_host_id,
                            "bk_cloud_id": host.bk_cloud_id,
                            "bk_biz_id": host.bk_biz_id,
                            "labels": host.labels,
                            "device_class": "IT5.4XLARGE32",
                            "cpu_num": 16,
                            "dram_cap": 32768,
                            "total_data_storage_cap": 500,
                            "storage_device": {"/data": {"size": 500, "disk_type": "NVME_SSD"}},
                            "os_name": "tlinux-2.6",
                        }
                    ]
                }
            ],
        }
        with patch.object(v2.DBResourceApi, "resource_apply", return_value=apply_resp), patch.object(
            v2, "backup_info_format", return_value={}
        ), patch.object(v2, "MySQLRollbackExerciseFlow") as flow_cls:
            ok = v2._submit_exercise_task(cand, host, [])

        self.assertTrue(ok)
        flow_cls.return_value.run.assert_called_once()
        task_row = MySQLBackupRecoverTask.objects.get(cluster_id=cluster.id)
        self.assertEqual(task_row.exercise_host_ip, "127.0.0.95")
        self.assertEqual(task_row.exercise_host_spec["device_class"], "IT5.4XLARGE32")
        self.assertEqual(task_row.exercise_host_spec["cpu_num"], 16)
        self.assertEqual(task_row.exercise_host_spec["dram_cap"], 32768)
        self.assertEqual(
            task_row.exercise_host_spec["storage_device"], {"/data": {"size": 500, "disk_type": "NVME_SSD"}}
        )

    def test_controller_resolve_exercise_host_spec_fallback(self):
        from backend.flow.engine.controller import mysql_backup_data_recovery_exercise as ctrl

        # 1) 入参已包含硬件字段时直接抽取，不查资源池
        with patch.object(ctrl.DBResourceApi, "resource_list") as mock_list:
            snap = ctrl._resolve_exercise_host_spec(
                {
                    "ip": "127.0.0.21",
                    "bk_cloud_id": 0,
                    "device_class": "S5.2XLARGE16",
                    "cpu_num": 8,
                }
            )
        mock_list.assert_not_called()
        self.assertEqual(snap["device_class"], "S5.2XLARGE16")

        # 2) 入参缺少硬件字段时按 (bk_cloud_id, ip) 查资源池补齐
        mock_resp = {
            "code": 0,
            "data": {
                "details": [
                    {
                        "ip": "127.0.0.22",
                        "bk_cloud_id": 1,
                        "device_class": "WRONG_CLOUD",
                    },
                    {
                        "ip": "127.0.0.22",
                        "bk_cloud_id": 0,
                        "device_class": "S5.4XLARGE32",
                        "cpu_num": 16,
                        "storage_device": {"/data": {"size": 800, "disk_type": "CLOUD_SSD"}},
                    },
                ]
            },
        }
        with patch.object(ctrl.DBResourceApi, "resource_list", return_value=mock_resp) as mock_list:
            snap = ctrl._resolve_exercise_host_spec({"ip": "127.0.0.22", "bk_host_id": 22, "bk_cloud_id": 0})
        mock_list.assert_called_once_with(
            params={"hosts": ["127.0.0.22"], "bk_cloud_id": 0, "limit": -1, "offset": 0}, raw=True
        )
        self.assertEqual(snap["device_class"], "S5.4XLARGE32")
        self.assertEqual(snap["cpu_num"], 16)
        self.assertEqual(snap["storage_device"]["/data"]["disk_type"], "CLOUD_SSD")

        # 3) 资源池异常时降级返回基础字段，不抛异常
        with patch.object(ctrl.DBResourceApi, "resource_list", side_effect=RuntimeError("timeout")):
            snap = ctrl._resolve_exercise_host_spec({"ip": "127.0.0.23", "bk_host_id": 23, "bk_cloud_id": 0})
        self.assertEqual(snap, {"ip": "127.0.0.23", "bk_host_id": 23, "bk_cloud_id": 0})
