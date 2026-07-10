# -*- coding: utf-8 -*-
from django.test import SimpleTestCase

from backend.flow.utils.mysql.dts.task_name import TASK_NAME_MAX_LEN, build_migrate_task_name, fit_task_name_max_len


class BuildMigrateTaskNameTest(SimpleTestCase):
    def test_one_to_one_short_name(self):
        name = build_migrate_task_name(12, [100], 200)
        self.assertEqual(name, "mysql-dts-12-100-200")
        self.assertLessEqual(len(name), TASK_NAME_MAX_LEN)

    def test_many_to_one_joins_srcs(self):
        name = build_migrate_task_name(12, [100, 101], 200)
        self.assertEqual(name, "mysql-dts-12-100_101-200")

    def test_one_to_many_differs_by_dst(self):
        name_a = build_migrate_task_name(12, [100], 201)
        name_b = build_migrate_task_name(12, [100], 202)
        self.assertEqual(name_a, "mysql-dts-12-100-201")
        self.assertEqual(name_b, "mysql-dts-12-100-202")
        self.assertNotEqual(name_a, name_b)

    def test_overlong_fits_and_stable(self):
        srcs = list(range(1000, 1100))
        name1 = build_migrate_task_name(999999, srcs, 200)
        name2 = build_migrate_task_name(999999, srcs, 200)
        self.assertLessEqual(len(name1), TASK_NAME_MAX_LEN)
        self.assertEqual(name1, name2)
        self.assertTrue(name1.startswith("mysql-dts-999999-"))

    def test_different_full_yields_different_hash_suffix(self):
        srcs_a = list(range(1000, 1100))
        srcs_b = list(range(2000, 2100))
        name_a = build_migrate_task_name(1, srcs_a, 200)
        name_b = build_migrate_task_name(1, srcs_b, 200)
        self.assertLessEqual(len(name_a), TASK_NAME_MAX_LEN)
        self.assertLessEqual(len(name_b), TASK_NAME_MAX_LEN)
        self.assertNotEqual(name_a, name_b)
        # 截断后末尾短哈希段应不同
        self.assertNotEqual(name_a[-8:], name_b[-8:])


class FitTaskNameMaxLenTest(SimpleTestCase):
    def test_short_unchanged(self):
        self.assertEqual(fit_task_name_max_len("mysql-dts-1-2-3"), "mysql-dts-1-2-3")

    def test_exact_max_unchanged(self):
        name = "x" * TASK_NAME_MAX_LEN
        self.assertEqual(fit_task_name_max_len(name), name)
