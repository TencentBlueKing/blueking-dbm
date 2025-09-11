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
import datetime

from db_services.redis.capacity_evaluate_service.repositories.cvm_repo import CONST_NVME_SSD_DISK_SIZE_4X, CvmSpec
from django.utils.dateparse import parse_datetime


class TestParseDatetime:
    """Test cases for parse datetime"""

    def test_parse_datetime(self):
        """test parse datetime"""
        datetime_str = "2025-09-05T06:22:40.073Z"
        datetime_obj = parse_datetime(datetime_str)
        assert datetime_obj == datetime.datetime(2025, 9, 5, 6, 22, 40, 73000, tzinfo=datetime.timezone.utc)


class TestCvmSpec:
    """Test cases for CvmSpec class"""

    disk_size_4x = CONST_NVME_SSD_DISK_SIZE_4X * 1024
    disk_size_8x = CONST_NVME_SSD_DISK_SIZE_4X * 2 * 1024
    device_class_key = "bk_svr_device_class_name"

    def test_from_host_case_1(self):
        """test from host info with none device class"""
        test_cases = [
            {
                "input": {self.device_class_key: "", "bk_cpu": 1, "bk_mem": 1, "bk_disk": 1},
                "output": CvmSpec("", 1000, 1, 1024, "", False),
            },
            {
                "input": {self.device_class_key: "S6.2XLARGE16", "bk_cpu": 1, "bk_mem": 1, "bk_disk": 100},
                "output": CvmSpec("S6.2XLARGE16", 8000, 16 * 1024, 100 * 1024, "", False),
            },
            {
                "input": {self.device_class_key: "S3.8XLARGE128", "bk_cpu": 1, "bk_mem": 1, "bk_disk": 1000},
                "output": CvmSpec("S3.8XLARGE128", 32 * 1000, 128 * 1024, 1000 * 1024, "", False),
            },
            {
                "input": {self.device_class_key: "ITA5.16XLARGE288", "bk_cpu": 1, "bk_mem": 1, "bk_disk": 1},
                "output": CvmSpec("ITA5.16XLARGE288", 16 * 4 * 1000, 288 * 1024, self.disk_size_8x, "NVME", True),
            },
            {
                "input": {self.device_class_key: "IT5.4xlarge64"},
                "output": CvmSpec("IT5.4xlarge64", 4 * 4 * 1000, 64 * 1024, self.disk_size_4x, "NVME", True),
            },
            {
                "input": {self.device_class_key: "IT5.8xlarge128"},
                "output": CvmSpec("IT5.8xlarge128", 8 * 4 * 1000, 128 * 1024, self.disk_size_8x, "NVME", True),
            },
            {
                "input": {self.device_class_key: "i6t.4xlarge56"},
                "output": CvmSpec("i6t.4xlarge56", 4 * 4 * 1000, 56 * 1024, self.disk_size_4x, "NVME", True),
            },
            {
                "input": {self.device_class_key: "i6t.8xlarge112"},
                "output": CvmSpec("i6t.8xlarge112", 8 * 4 * 1000, 112 * 1024, self.disk_size_8x, "NVME", True),
            },
            {
                "input": {self.device_class_key: "sa3.4xlarge64", "bk_disk": 1000},
                "output": CvmSpec("sa3.4xlarge64", 4 * 4 * 1000, 64 * 1024, 1000 * 1024, "", False),
            },
            {
                "input": {self.device_class_key: "sa3.8xlarge128", "bk_disk": 1000},
                "output": CvmSpec("sa3.8xlarge128", 8 * 4 * 1000, 128 * 1024, 1000 * 1024, "", False),
            },
        ]

        for i, test_case in enumerate(test_cases):
            cvm_spec = CvmSpec.from_host_info(test_case["input"])
            assert cvm_spec.cpu_core_m == test_case["output"].cpu_core_m
            assert cvm_spec.mem_total_m == test_case["output"].mem_total_m
            assert cvm_spec.disk_size_total_m == test_case["output"].disk_size_total_m
            assert cvm_spec.disk_type == test_case["output"].disk_type.upper()
            assert cvm_spec.is_nvme_ssd == test_case["output"].is_nvme_ssd
            assert cvm_spec.device_class == test_case["output"].device_class
