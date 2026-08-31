# -*- coding: utf-8 -*-
from django.test import SimpleTestCase

from backend.flow.utils.mysql.dts.constants import MigrateTopology
from backend.flow.utils.mysql.dts.task_name import (
    TASK_NAME_MAX_LEN,
    build_migrate_task_name,
    fit_task_name_max_len,
    patch_migrate_task_names_into_details,
)


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

    def test_uniqueness_token_keeps_max_len(self):
        name = build_migrate_task_name(12, [100], 200, uniqueness_token="abcdef123456")
        self.assertEqual(name, "mysql-dts-12-100-200-abcdef123456")
        self.assertLessEqual(len(name), TASK_NAME_MAX_LEN)

    def test_uniqueness_token_on_overlong_still_fits(self):
        srcs = list(range(1000, 1100))
        name = build_migrate_task_name(999999, srcs, 200, uniqueness_token="abcdef123456")
        self.assertLessEqual(len(name), TASK_NAME_MAX_LEN)
        self.assertTrue(name.endswith("-abcdef123456"))


class PatchInfosTaskNameUniqueTest(SimpleTestCase):
    def test_same_src_dst_rows_get_distinct_random_suffix(self):
        details = {
            "infos": [
                {
                    "migrate": {
                        "topology": MigrateTopology.ONE_TO_ONE.value,
                        "one_to_one": {
                            "source": {"cluster_id": 100, "sync_scope": {"do_dbs": ["db_a"]}},
                            "target": {"cluster_id": 200},
                        },
                    }
                },
                {
                    "migrate": {
                        "topology": MigrateTopology.ONE_TO_ONE.value,
                        "one_to_one": {
                            "source": {"cluster_id": 100, "sync_scope": {"do_dbs": ["db_b"]}},
                            "target": {"cluster_id": 200},
                        },
                    }
                },
            ]
        }
        patch_migrate_task_names_into_details(details, 18801)
        name0 = details["infos"][0]["migrate"]["one_to_one"]["task_name"]
        name1 = details["infos"][1]["migrate"]["one_to_one"]["task_name"]
        self.assertRegex(name0, r"^mysql-dts-18801-100-200-[0-9a-f]{12}$")
        self.assertRegex(name1, r"^mysql-dts-18801-100-200-[0-9a-f]{12}$")
        self.assertNotEqual(name0, name1)
        patch_migrate_task_names_into_details(details, 18801)
        self.assertEqual(details["infos"][0]["migrate"]["one_to_one"]["task_name"], name0)


class FitTaskNameMaxLenTest(SimpleTestCase):
    def test_max_len_strictly_under_50(self):
        self.assertLess(TASK_NAME_MAX_LEN, 50)

    def test_short_unchanged(self):
        self.assertEqual(fit_task_name_max_len("mysql-dts-1-2-3"), "mysql-dts-1-2-3")

    def test_exact_max_unchanged(self):
        name = "x" * TASK_NAME_MAX_LEN
        self.assertEqual(fit_task_name_max_len(name), name)

    def test_fifty_chars_truncated_to_max(self):
        fitted = fit_task_name_max_len("x" * 50)
        self.assertEqual(len(fitted), TASK_NAME_MAX_LEN)
        self.assertLess(len(fitted), 50)
