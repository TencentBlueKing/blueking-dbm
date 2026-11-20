# -*- coding: utf-8 -*-
import copy
from unittest.mock import patch

from django.test import TestCase

from backend.db_meta.api.cluster.jobhost.create import create
from backend.db_meta.enums import AccessLayer, ClusterType, MachineType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import BKCity, Cluster, ClusterEntry, LogicalCity, Machine
from backend.db_meta.models.job_host import JobHost, JobHostStatus
from backend.tests.mock_data import constant
from backend.tests.mock_data.components import cc

TEST_BK_CLOUD_ID = 0
TEST_NAME = "jobhost-ut-01"


def _cc_api_mock_cloud0():
    hosts = copy.deepcopy(cc.MOCK_LIST_HOSTS_WITHOU_BIZ_RETURN)
    for info in hosts["info"]:
        info["bk_cloud_id"] = TEST_BK_CLOUD_ID
    return cc.CCApiMock(list_hosts_without_biz_return=hosts)


class JobHostCreateTest(TestCase):
    def setUp(self):
        logical, _ = LogicalCity.objects.get_or_create(id=1, defaults={"name": "南京"})
        BKCity.objects.get_or_create(
            bk_idc_city_id=cc.REGISTERED_CITY_ID,
            defaults={"logical_city": logical, "bk_idc_city_name": "南京"},
        )

    @patch("backend.db_meta.api.machine.apis.CCApi", _cc_api_mock_cloud0())
    def test_create_only_writes_job_host_and_machine(self):
        job = create(
            bk_biz_id=constant.BK_BIZ_ID,
            bk_cloud_id=TEST_BK_CLOUD_ID,
            name=TEST_NAME,
            ip=cc.NORMAL_IP,
            deploy_path="/data/mongo-dts",
            db_type="mongodb",
            purpose="mongoshake_dts",
            creator="tester",
        )
        self.assertEqual(job.status, JobHostStatus.RUNNING.value)
        self.assertEqual(job.db_type, "mongodb")
        self.assertTrue(JobHost.objects.filter(id=job.id).exists())
        self.assertTrue(Machine.objects.filter(ip=cc.NORMAL_IP, bk_cloud_id=TEST_BK_CLOUD_ID).exists())
        machine = Machine.objects.get(ip=cc.NORMAL_IP, bk_cloud_id=TEST_BK_CLOUD_ID)
        self.assertEqual(machine.machine_type, MachineType.JOB_HOST.value)
        self.assertFalse(Cluster.objects.filter(cluster_type=ClusterType.JobHost.value, name=TEST_NAME).exists())
        self.assertFalse(ClusterEntry.objects.filter(entry=cc.NORMAL_IP).exists())

    @patch("backend.db_meta.api.machine.apis.CCApi", _cc_api_mock_cloud0())
    def test_create_rejects_duplicate_active_name(self):
        create(
            bk_biz_id=constant.BK_BIZ_ID,
            bk_cloud_id=TEST_BK_CLOUD_ID,
            name=TEST_NAME,
            ip=cc.NORMAL_IP,
            creator="tester",
        )
        with self.assertRaises(DBMetaException):
            create(
                bk_biz_id=constant.BK_BIZ_ID,
                bk_cloud_id=TEST_BK_CLOUD_ID,
                name=TEST_NAME,
                ip=cc.NORMAL_IP2,
                creator="tester",
            )

    @patch("backend.db_meta.api.machine.apis.CCApi", _cc_api_mock_cloud0())
    def test_create_rejects_existing_non_job_host_machine(self):
        city = BKCity.objects.get(bk_idc_city_id=cc.REGISTERED_CITY_ID)
        Machine.objects.create(
            ip=cc.NORMAL_IP,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.MONGODB.value,
            bk_city=city,
            access_layer=AccessLayer.STORAGE.value,
            bk_host_id=200099,
            bk_cloud_id=TEST_BK_CLOUD_ID,
            cluster_type=ClusterType.MongoReplicaSet.value,
        )
        with self.assertRaises(DBMetaException):
            create(
                bk_biz_id=constant.BK_BIZ_ID,
                bk_cloud_id=TEST_BK_CLOUD_ID,
                name=TEST_NAME,
                ip=cc.NORMAL_IP,
                creator="tester",
            )

    @patch("backend.db_meta.api.machine.apis.CCApi", _cc_api_mock_cloud0())
    def test_create_rejects_active_job_host_same_ip(self):
        create(
            bk_biz_id=constant.BK_BIZ_ID,
            bk_cloud_id=TEST_BK_CLOUD_ID,
            name=TEST_NAME,
            ip=cc.NORMAL_IP,
            creator="tester",
        )
        with self.assertRaises(DBMetaException):
            create(
                bk_biz_id=constant.BK_BIZ_ID,
                bk_cloud_id=TEST_BK_CLOUD_ID,
                name="jobhost-ut-02",
                ip=cc.NORMAL_IP,
                creator="tester",
            )
