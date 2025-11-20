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


CONST_NVME_SSD_DISK_SIZE_4X = 1700
"""
CONST_NVME_SSD_DISK_SIZE_4X it类机器, 4xlarge机型分配nvme磁盘的Size
这里用固定的值，因为要兼容新旧机型，所以这里用固定的值
查云接口可以获取实际磁盘大小
"""


class CvmSpec:
    """cvm spec"""

    def __init__(
        self, device_class="", cpu_core_m=0, mem_total_m=0, disk_size_total_m=0, disk_type="", is_nvme_ssd=False
    ):
        self.device_class = device_class
        self.cpu_core_m = cpu_core_m
        self.mem_total_m = mem_total_m
        self.disk_size_total_m = disk_size_total_m
        self.disk_type = disk_type
        self.is_nvme_ssd = is_nvme_ssd

    @classmethod
    def from_host_info(cls, host_info: dict) -> "CvmSpec":
        """从主机信息中获取CvmSpec"""
        device_class = host_info.get("bk_svr_device_class_name", "")
        bk_cpu = host_info.get("bk_cpu", 0)
        bk_mem = host_info.get("bk_mem", 0)
        bk_disk = host_info.get("bk_disk", 0)
        if device_class == "" or device_class is None:
            return CvmSpec(
                device_class=device_class,
                cpu_core_m=bk_cpu * 1000,
                mem_total_m=bk_mem,
                disk_size_total_m=bk_disk * 1024,
                disk_type="",
                is_nvme_ssd=False,
            )
        elif "." in device_class:
            return cls.parse_device_class(device_class, bk_disk * 1024)
        else:
            return None

    @classmethod
    def parse_device_class(cls, device_class: str, disk_size_total_m: int = 0) -> "CvmSpec":
        """parse device class to cvm spec"""
        if "." in device_class:
            cvm_type, cpu_core, mem = cls.parse_txyun_device_class(device_class)
            if cvm_type.startswith("I"):
                disk_type = "NVME"
                if cpu_core == 16:
                    disk_size_total = CONST_NVME_SSD_DISK_SIZE_4X
                elif cpu_core >= 32:
                    disk_size_total = CONST_NVME_SSD_DISK_SIZE_4X * 2

                return CvmSpec(
                    device_class=device_class,
                    cpu_core_m=cpu_core * 1000,
                    mem_total_m=mem * 1024,
                    disk_size_total_m=disk_size_total * 1024,
                    disk_type=disk_type,
                    is_nvme_ssd=True,
                )
            else:
                # 非it类，磁盘大小从参数中获取
                return CvmSpec(
                    device_class=device_class,
                    cpu_core_m=cpu_core * 1000,
                    mem_total_m=mem * 1024,
                    disk_size_total_m=disk_size_total_m,
                    disk_type="",
                    is_nvme_ssd=False,
                )
        else:
            cvm_type, cpu, mem = None, None, None
        return cvm_type, cpu, mem

    @classmethod
    def parse_txyun_device_class(cls, cvm_name: str):
        """parse txyun device class to cvm spec"""
        cvm_name = cvm_name.upper()
        cvm_type, cpu, mem = None, None, None
        parts = cvm_name.split(".")
        if len(parts) != 2:
            raise ValueError(f"Invalid CVM type: {cvm_name}")

        cvm_type = parts[0]
        # Determine CPU multiplier based on size
        if "LARGE" in parts[1]:
            n_cpu = 4
            cpu_spec = parts[1].split("LARGE")
        elif "MEDIUM" in parts[1]:
            n_cpu = 2
            cpu_spec = parts[1].split("MEDIUM")
        elif "SMALL" in parts[1]:
            n_cpu = 1
            cpu_spec = parts[1].split("SMALL")
        else:
            raise ValueError("Invalid CVM type")

        if len(cpu_spec) != 2:
            raise ValueError("Invalid CVM type")

        # Calculate total CPU cores
        cpu_multiplier = cpu_spec[0].rstrip("X")
        if cpu_multiplier == "":
            cpu = n_cpu
        else:
            try:
                cpu = int(cpu_multiplier) * n_cpu
            except ValueError:
                raise ValueError("Invalid CVM type")

        # Get memory size - fix the bug here
        try:
            mem_multiplier = cpu_spec[1].rstrip("X")
            mem = int(mem_multiplier)
        except ValueError:
            raise ValueError("Invalid CVM type")

        return cvm_type, cpu, mem

    def to_spec(self):
        """convert cvm spec to string"""
        return f"{self.cpu_core_m}c{self.mem_total_m}g{self.disk_size_total_m}g({self.disk_type})"

    def __json__(self):
        return {
            "device_class": self.device_class,
            "cpu_core_m": self.cpu_core_m,
            "mem_total_m": self.mem_total_m,
            "disk_size_total_m": self.disk_size_total_m,
            "disk_type": self.disk_type,
            "is_nvme_ssd": self.is_nvme_ssd,
        }

    def __dict__(self):
        return self.__json__()
