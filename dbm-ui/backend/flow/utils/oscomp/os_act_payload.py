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
from dataclasses import dataclass
from typing import Any, Dict, Optional

from backend.flow.consts import DBActuatorActionEnum, DBActuatorTypeEnum


@dataclass
class DiskBenchmarkContext:
    """
    BaselineDiskBenchmarkFlow 的 trans_data dataclass
    actuator 的输出会被 ExecuteDBActuatorScriptComponent 写入 benchmark_result 字段
    下游的 BaselineDiskWriteComponent 从这里读出 5 个性能指标
    """

    benchmark_result: Optional[Dict[str, Any]] = None


class OSActPayload:
    """
    OS 层面通用 actuator payload 构造器
    与具体数据库产品无关, 用于触发 dbactuator 的 os 顶级 group 子命令

    构造函数签名与 MysqlActPayload 保持一致, 因为 ExecuteDBActuatorScriptComponent
    会按相同方式实例化 (见 plugins/components/collections/mysql/exec_actuator_script.py)
    """

    def __init__(
        self,
        bk_cloud_id: int,
        ticket_data: Optional[dict] = None,
        cluster: Optional[dict] = None,
        cluster_type: Optional[str] = None,
    ):
        self.bk_cloud_id = bk_cloud_id
        self.ticket_data = ticket_data or {}
        self.cluster = cluster or {}
        self.cluster_type = cluster_type
        # OS 操作不需要 mysql 系列账号, runtime_account 给空 dict 即可
        self.account: Dict[str, Any] = {}

    def get_disk_benchmark_payload(self, ip: str, trans_data, **kwargs) -> dict:
        """
        构造 ./dbactuator os disk-benchmark 的执行 payload
        kwargs (来自 act 的 component_kwargs):
            target          : 测试文件绝对路径 (必填), 不能以 /dev/ 开头
            size            : 测试文件大小, 默认 8G
            runtime         : 每个 phase 持续时间(秒), 默认 30
            jobs            : 随机 IO 并发数, 默认 64
            throughput_jobs : 顺序 IO 并发数, 默认 16
        """
        return {
            "db_type": DBActuatorTypeEnum.OS.value,
            "action": DBActuatorActionEnum.DiskBenchmark.value,
            "payload": {
                "general": {"runtime_account": self.account},
                "extend": {
                    "target": kwargs["target"],
                    "size": kwargs.get("size", "8G"),
                    "runtime": kwargs.get("runtime", 30),
                    "jobs": kwargs.get("jobs", 64),
                    "throughput_jobs": kwargs.get("throughput_jobs", 16),
                },
            },
        }
