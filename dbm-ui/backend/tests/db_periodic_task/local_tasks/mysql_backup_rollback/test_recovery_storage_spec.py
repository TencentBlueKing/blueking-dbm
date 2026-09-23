# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from django.test import TestCase

MOD = "backend.db_periodic_task.local_tasks.mysql_backup_rollback.gen_task"


class RecoveryStorageSpecDiskGateTest(TestCase):
    def _call(self, storage_spec, min_gb=100):
        cluster = MagicMock()
        cluster.immute_domain = "exercise.db"
        with patch(f"{MOD}.calculate_recovery_min_disk_size_gb", return_value=min_gb), patch(
            f"{MOD}.get_master_storage_spec", return_value=storage_spec
        ):
            from backend.db_periodic_task.local_tasks.mysql_backup_rollback.gen_task import build_recovery_storage_spec

            return build_recovery_storage_spec(cluster, 1, "innodb", "logical", 1)

    def test_one_disk_stays_single_disk(self):
        spec = self._call([{"min": 50, "mount_point": "/data"}])
        self.assertEqual(spec, [{"max": 2147483647, "min": 100}])

    def test_two_disks_keep_mount_points(self):
        spec = self._call(
            [
                {"min": 20, "mount_point": "/data"},
                {"min": 30, "mount_point": "/data1"},
            ]
        )
        self.assertEqual(
            spec,
            [
                {"max": 2147483647, "min": 20, "mount_point": "/data"},
                {"max": 2147483647, "min": 100, "mount_point": "/data1"},
            ],
        )

    def test_three_disks_keep_first_two(self):
        spec = self._call(
            [
                {"min": 20, "mount_point": "/data"},
                {"min": 30, "mount_point": "/data1"},
                {"min": 40, "mount_point": "/data2"},
            ]
        )
        mounts = [item.get("mount_point") for item in spec]
        self.assertEqual(mounts, ["/data", "/data1"])

    def test_data_disk_uses_calculated_when_at_most_half(self):
        spec = self._call(
            [
                {"min": 20, "mount_point": "/data"},
                {"min": 200, "mount_point": "/data1"},
            ],
            min_gb=100,
        )
        self.assertEqual(spec[1]["min"], 100)
        self.assertEqual(spec[0]["min"], 20)

    def test_data_disk_keeps_larger_when_above_half(self):
        spec = self._call(
            [
                {"min": 20, "mount_point": "/data"},
                {"min": 150, "mount_point": "/data1"},
            ],
            min_gb=100,
        )
        self.assertEqual(spec[1]["min"], 150)
