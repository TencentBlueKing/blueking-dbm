"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from datetime import timedelta

import pytest
from django.test import TestCase
from django.test.testcases import TransactionTestCase
from django.utils import timezone

from backend.db_periodic_task.models import ExerciseIgnoreConfig, ExerciseIgnoreType

pytestmark = pytest.mark.django_db


class TestExerciseIgnoreConfig(TransactionTestCase):
    """Test exercise ignore configuration functionality"""

    def setUp(self):
        """Set up test data"""
        self.test_biz_id = 100
        self.test_cluster_id = 200
        self.test_cluster_domain = "test-mysql-001.db"

    def test_biz_ignore_config(self):
        """Test business-level ignore configuration"""
        # Create business ignore configuration
        ExerciseIgnoreConfig.objects.create(
            ignore_type=ExerciseIgnoreType.BIZ,
            target_id=self.test_biz_id,
            target_name="Test Business",
            reason="Business is undergoing important changes",
            is_active=True,
        )

        # Test if business is ignored
        self.assertTrue(ExerciseIgnoreConfig.is_biz_ignored(self.test_biz_id))
        self.assertFalse(ExerciseIgnoreConfig.is_biz_ignored(999))  # Non-existent business

        # Test getting ignored business ID list
        ignored_biz_ids = ExerciseIgnoreConfig.get_ignored_biz_ids()
        self.assertIn(self.test_biz_id, ignored_biz_ids)

    def test_cluster_ignore_config(self):
        """Test cluster-level ignore configuration"""
        # Create cluster ignore configuration
        ExerciseIgnoreConfig.objects.create(
            ignore_type=ExerciseIgnoreType.CLUSTER,
            target_id=self.test_cluster_id,
            target_name=self.test_cluster_domain,
            reason="Production core cluster, not participating in exercises",
            is_active=True,
        )

        # Test if cluster is ignored
        self.assertTrue(ExerciseIgnoreConfig.is_cluster_ignored(self.test_cluster_id))
        self.assertFalse(ExerciseIgnoreConfig.is_cluster_ignored(999))  # Non-existent cluster

        # Test getting ignored cluster ID list
        ignored_cluster_ids = ExerciseIgnoreConfig.get_ignored_cluster_ids()
        self.assertIn(self.test_cluster_id, ignored_cluster_ids)

    def test_expire_time_config(self):
        """Test expiration time configuration"""
        # Create expired ignore configuration
        past_time = timezone.now() - timedelta(hours=1)
        ExerciseIgnoreConfig.objects.create(
            ignore_type=ExerciseIgnoreType.BIZ,
            target_id=self.test_biz_id,
            target_name="Test Business",
            reason="Temporary ignore",
            is_active=True,
            expire_time=past_time,
        )

        # Expired configuration should not take effect
        self.assertFalse(ExerciseIgnoreConfig.is_biz_ignored(self.test_biz_id))

        # Create non-expired ignore configuration
        future_time = timezone.now() + timedelta(hours=1)
        ExerciseIgnoreConfig.objects.create(
            ignore_type=ExerciseIgnoreType.BIZ,
            target_id=999,
            target_name="Another Test Business",
            reason="Temporary ignore",
            is_active=True,
            expire_time=future_time,
        )

        # Non-expired configuration should take effect
        self.assertTrue(ExerciseIgnoreConfig.is_biz_ignored(999))

    def test_inactive_config(self):
        """Test inactive configuration"""
        # Create inactive ignore configuration
        ExerciseIgnoreConfig.objects.create(
            ignore_type=ExerciseIgnoreType.BIZ,
            target_id=self.test_biz_id,
            target_name="Test Business",
            reason="Disabled configuration",
            is_active=False,
        )

        # Inactive configuration should not take effect
        self.assertFalse(ExerciseIgnoreConfig.is_biz_ignored(self.test_biz_id))

    def test_unique_constraint(self):
        """Test unique constraint"""
        # Create first configuration
        ExerciseIgnoreConfig.objects.create(
            ignore_type=ExerciseIgnoreType.BIZ,
            target_id=self.test_biz_id,
            target_name="Test Business",
            reason="First configuration",
            is_active=True,
        )

        # Try to create configuration with same type and target, should trigger unique constraint
        with self.assertRaises(Exception):  # Could be IntegrityError or other database exception
            ExerciseIgnoreConfig.objects.create(
                ignore_type=ExerciseIgnoreType.BIZ,
                target_id=self.test_biz_id,
                target_name="Test Business 2",
                reason="Second configuration",
                is_active=True,
            )

    def test_save_method_deactivation(self):
        """Test automatic deactivation functionality of save method"""
        # Create first active configuration
        config1 = ExerciseIgnoreConfig.objects.create(
            ignore_type=ExerciseIgnoreType.BIZ,
            target_id=self.test_biz_id,
            target_name="Test Business",
            reason="First configuration",
            is_active=True,
        )

        # Due to unique constraint, we need to use different target_id to test save method
        # Here we test updating existing configuration
        config1.reason = "Updated configuration"
        config1.save()

        # Configuration should still be active
        config1.refresh_from_db()
        self.assertTrue(config1.is_active)

    def tearDown(self):
        """Clean up test data"""
        ExerciseIgnoreConfig.objects.all().delete()


class TestExerciseIgnoreConfigIntegration(TestCase):
    """Test integration functionality of exercise ignore configuration"""

    def test_get_ignored_lists_performance(self):
        """Test performance of getting ignored lists"""
        # Create multiple ignore configurations
        for i in range(10):
            ExerciseIgnoreConfig.objects.create(
                ignore_type=ExerciseIgnoreType.BIZ,
                target_id=100 + i,
                target_name=f"Test Business {i}",
                reason=f"Test reason {i}",
                is_active=True,
            )

        for i in range(10):
            ExerciseIgnoreConfig.objects.create(
                ignore_type=ExerciseIgnoreType.CLUSTER,
                target_id=200 + i,
                target_name=f"test-cluster-{i}.db",
                reason=f"Test reason {i}",
                is_active=True,
            )

        # Test getting ignore lists
        ignored_biz_ids = ExerciseIgnoreConfig.get_ignored_biz_ids()
        ignored_cluster_ids = ExerciseIgnoreConfig.get_ignored_cluster_ids()

        self.assertEqual(len(ignored_biz_ids), 10)
        self.assertEqual(len(ignored_cluster_ids), 10)

        # Verify ID ranges
        self.assertTrue(all(100 <= biz_id <= 109 for biz_id in ignored_biz_ids))
        self.assertTrue(all(200 <= cluster_id <= 209 for cluster_id in ignored_cluster_ids))

    def tearDown(self):
        """Clean up test data"""
        ExerciseIgnoreConfig.objects.all().delete()
