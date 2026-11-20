# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from django.test import TestCase

from backend.db_meta.api.cluster.jobhost.decommission import decommission
from backend.db_meta.enums import AccessLayer, ClusterType, MachineType
from backend.db_meta.models import BKCity, LogicalCity, Machine
from backend.db_meta.models.job_host import JobHost, JobHostStatus
from backend.tests.mock_data import constant
from backend.tests.mock_data.components import cc

TEST_BK_CLOUD_ID = 0


class JobHostDecommissionTest(TestCase):
    def setUp(self):
        logical, _ = LogicalCity.objects.get_or_create(id=1, defaults={"name": "南京"})
        self.bk_city, _ = BKCity.objects.get_or_create(
            bk_idc_city_id=1,
            defaults={"logical_city": logical, "bk_idc_city_name": "南京"},
        )

    def _create_job(self):
        Machine.objects.create(
            ip=cc.NORMAL_IP,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.JOB_HOST.value,
            bk_city=self.bk_city,
            access_layer=AccessLayer.PROXY.value,
            bk_host_id=200001,
            bk_cloud_id=TEST_BK_CLOUD_ID,
            cluster_type=ClusterType.JobHost.value,
        )
        return JobHost.objects.create(
            name="jobhost-decom-01",
            bk_biz_id=constant.BK_BIZ_ID,
            bk_cloud_id=TEST_BK_CLOUD_ID,
            status=JobHostStatus.RUNNING.value,
            ip=cc.NORMAL_IP,
            deploy_path="/data/mongo-dts",
            db_type="mongodb",
            purpose="mongoshake_dts",
        )

    @patch("backend.db_meta.api.cluster.jobhost.decommission.CcManage")
    def test_decommission_recycles_machine(self, mock_cc_manage):
        mock_cc_manage.return_value = MagicMock()
        job = self._create_job()
        decommission(job_host_id=job.id, recycle_hosts=True, updater="tester")
        job.refresh_from_db()
        self.assertEqual(job.status, JobHostStatus.DESTROYED.value)
        self.assertFalse(Machine.objects.filter(bk_host_id=200001).exists())
        mock_cc_manage.return_value.recycle_host.assert_called_once_with([200001])

    @patch("backend.db_meta.api.cluster.jobhost.decommission.CcManage")
    def test_decommission_skips_non_job_host_machine(self, mock_cc_manage):
        mock_cc_manage.return_value = MagicMock()
        Machine.objects.create(
            ip=cc.NORMAL_IP,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.MONGODB.value,
            bk_city=self.bk_city,
            access_layer=AccessLayer.STORAGE.value,
            bk_host_id=200002,
            bk_cloud_id=TEST_BK_CLOUD_ID,
            cluster_type=ClusterType.MongoReplicaSet.value,
        )
        job = JobHost.objects.create(
            name="jobhost-decom-skip",
            bk_biz_id=constant.BK_BIZ_ID,
            bk_cloud_id=TEST_BK_CLOUD_ID,
            status=JobHostStatus.RUNNING.value,
            ip=cc.NORMAL_IP,
            deploy_path="/data/mongo-dts",
            db_type="mongodb",
            purpose="mongoshake_dts",
        )
        decommission(job_host_id=job.id, recycle_hosts=True, updater="tester")
        job.refresh_from_db()
        self.assertEqual(job.status, JobHostStatus.DESTROYED.value)
        self.assertTrue(Machine.objects.filter(bk_host_id=200002).exists())
        mock_cc_manage.return_value.recycle_host.assert_not_called()
