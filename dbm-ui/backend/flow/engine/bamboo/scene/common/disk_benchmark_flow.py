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
import copy
import logging
import os
import re
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import gettext as _
from pipeline.exceptions import InvalidOperationException

from backend import env
from backend.configuration.constants import DBType
from backend.db_services.dbresource.machine_storage import fetch_merged_storage_device_for_hosts
from backend.flow.consts import DBA_ROOT_USER, LONG_JOB_TIMEOUT
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.baseline_disk_writer import BaselineDiskWriteComponent
from backend.flow.plugins.components.collections.common.sa_idle_check import CheckMachineIdleComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.common_act_dataclass import InitCheckForResourceKwargs
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.oscomp.os_act_payload import DiskBenchmarkContext, OSActPayload

logger = logging.getLogger("flow")

# target 路径白名单, 与 Serializer / actuator 端保持一致
# 详见 dbm-services/mysql/db-tools/dbactuator/pkg/components/oscomp/disk_benchmark.go
_ALLOWED_TARGET_PREFIXES = ("/data/", "/data1/", "/tmp/", "/var/tmp/")

_DATA_MOUNT_PREFIX_RE = re.compile(r"^(/data[0-9]*)(/|$)")


def _data_mount_prefix_from_target(target: str) -> Optional[str]:
    """从压测 target 路径解析数据盘挂载点前缀 /data、/data1 等；/tmp 等非 data 盘路径返回 None。"""
    norm = os.path.normpath(target or "")
    m = _DATA_MOUNT_PREFIX_RE.match(norm)
    return m.group(1) if m else None


class BaselineDiskBenchmarkFlow(object):
    """
    BaselineDisk 性能基线采集流程

    架构：多机并发, 每机子流程 = [机器空闲检查 -> 多盘串行 (actuator + 写库)]

    核心安全约束：
        - flow 入参起始处拒绝任何 target 以 /dev/ 开头, 只支持文件路径压测
        - 机器层走 SOPs 空闲检查 (CheckMachineIdleComponent)
        - actuator 层在跑测前再做一次 DB 进程黑名单检查 (在 dbactuator 内部做)

    入参 (来自 ticket_data) 示例:
        - target 在 /data、/data1 等数据盘路径下, 可省略 disk_name、disk_type、capacity_gb、is_local,
          流程在校验后会调用 fetch_merged_storage_device_for_hosts(与 fill_machine_storage_device 同源) 按挂载点回填
          capacity_gb / disk_type / is_local, 并生成 disk_name(形如 NVME_SSD_3570)。
        - target 在 /tmp 等路径下合并采集无法解析数据盘时, 须自行提供 disk_name。
        - disk_model 不入库, 写 BaselineDisk 时留空。
        - is_local 默认 False; IT 开头机型(本地盘)由合并结果置为 True。
        - 无需传机型: IT 本地盘判定由 CVM instanceType 兜底, 不再需要入参 bk_svr_device_cls_name。
    {
        "uid": "<unique_uid>",
        "created_by": "admin",
        "ticket_type": "OS_DISK_BENCHMARK",
        "bk_biz_id": 100100,
        "bk_cloud_id": 0,
        "strict_idle_check": false,
        "runtime": 30,
        "jobs": 64,
        "throughput_jobs": 16,
        "hosts": [
            {
                "ip": "127.0.0.1",
                "bk_cloud_id": 0,
                "disks": [
                    {
                        "target": "/data/baseline_bench/fio.bin",
                        "test_file_size": "8G"
                    }
                ]
            }
        ]
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data or {}

    def _validate(self):
        """
        flow 入参起始处的硬性校验, 任何不合法立即抛 InvalidOperationException

        校验项:
            - hosts 非空, 每个 host 有 ip
            - disks 非空, 每个 disk 有 target
            - target 是绝对路径
            - target 不以 /dev/ 开头 (拒裸盘)
            - target 落在白名单目录下 (拒系统关键文件)
            - disk_name: 必填, 除非 target 在 /dataN 下(由后续合并回填 disk_type/容量后生成 disk_name)

        这是与 Serializer / actuator 三层中的中间一层, 即便其它两层失效, 这里也会挡住。
        """
        hosts = self.data.get("hosts") or []
        if not hosts:
            raise InvalidOperationException(_("hosts 不能为空"))
        for h in hosts:
            if not h.get("ip"):
                raise InvalidOperationException(_("每个 host 必须包含 ip 字段"))
            disks = h.get("disks") or []
            if not disks:
                raise InvalidOperationException(_("host {} 的 disks 不能为空").format(h["ip"]))
            for d in disks:
                target = d.get("target") or ""
                if not target:
                    raise InvalidOperationException(_("host {} 存在 disk 缺少 target").format(h["ip"]))
                if not target.startswith("/"):
                    raise InvalidOperationException(_("disk.target 必须是绝对路径, got {}").format(target))
                if target.startswith("/dev/"):
                    raise InvalidOperationException(
                        _("拒绝执行: disk.target 不允许指向 /dev/ 设备节点 ({}). 本流程只支持文件模式压测").format(target)
                    )
                # 规范化 (防 ../ 注入), 再检查白名单
                cleaned = os.path.normpath(target)
                if not cleaned.startswith(_ALLOWED_TARGET_PREFIXES):
                    raise InvalidOperationException(
                        _("拒绝执行: disk.target 必须落在白名单目录 {} 下, got {} (规范化后 {})").format(
                            list(_ALLOWED_TARGET_PREFIXES), target, cleaned
                        )
                    )
                if not d.get("disk_name"):
                    if _data_mount_prefix_from_target(target):
                        # target 落在 /dataN 时, disk_name / disk_type / capacity_gb 均可由合并结果回填
                        continue
                    raise InvalidOperationException(
                        _("host {} 的 disk {} 缺少 disk_name (target 在 /dataN 时可省略, 由流程合并回填后生成)").format(h["ip"], target)
                    )

    def _validate_disk_identity_after_enrich(self) -> None:
        """合并回填后每块盘须具备 disk_name, 否则后续写 BaselineDisk 与 actuator 展示无键可用。"""
        for h in self.data.get("hosts") or []:
            ip = h.get("ip") or ""
            for d in h.get("disks") or []:
                target = d.get("target") or ""
                if not d.get("disk_name"):
                    raise InvalidOperationException(
                        _("host {} 的 disk {} 在合并回填后仍缺少 disk_name, 请确认 CVM/Job 采集成功且能解析出 disk_type 与容量").format(
                            ip, target
                        )
                    )

    def _enrich_hosts_disks_from_merged_storage(self) -> None:
        """
        按 fill_machine_storage_device 同源逻辑拉取 CVM+Job 合并的 storage_device,
        为落在 /dataN 下的 target 回填 capacity_gb / disk_type / is_local, 并刷新 disk_name。
        - disk_type: 入参未给出时, 用合并结果(CVM 云盘类型, 或 IT 本地盘的 NVME_SSD)兜底
        - is_local: 入参未显式给出时, 用合并结果(IT 开头机型为 True, 否则 False)
        """
        hosts = self.data.get("hosts") or []
        meta = []
        for h in hosts:
            ip = h.get("ip")
            if not ip:
                continue
            meta.append(
                {
                    "ip": ip,
                    "bk_cloud_id": int(h.get("bk_cloud_id", self.data.get("bk_cloud_id", 0))),
                    # 不再要求入参传机型: IT 本地盘判定改由 CVM instanceType(等价 bk_svr_device_cls_name) 兜底
                }
            )
        if not meta:
            return
        merged = fetch_merged_storage_device_for_hosts(meta)
        if not merged:
            logger.warning(_("未能从 CVM/Job 合并得到任何主机的 storage_device, 使用入参原有磁盘容量等元数据"))
            return
        for h in hosts:
            ip = h.get("ip")
            if not ip:
                continue
            sd = merged.get(ip)
            if not sd:
                continue
            for disk in h.get("disks") or []:
                mp = _data_mount_prefix_from_target(disk.get("target", ""))
                if not mp:
                    continue
                info = sd.get(mp)
                if not info:
                    continue
                self._apply_merged_disk_info(disk, info)

    @staticmethod
    def _apply_merged_disk_info(disk: Dict, info: Dict) -> None:
        """用合并结果回填单块盘的 capacity_gb / disk_type / is_local, 并据此刷新 disk_name。"""
        sz = info.get("size")
        if sz is not None:
            try:
                disk["capacity_gb"] = int(sz)
            except (TypeError, ValueError):
                pass
        # disk_type: 入参优先, 缺失时用合并结果兜底
        if not disk.get("disk_type") and info.get("disk_type"):
            disk["disk_type"] = info["disk_type"]
        # is_local: 入参显式给出则尊重, 否则用合并结果(IT 机型 True, 否则 False)
        if disk.get("is_local") is None:
            disk["is_local"] = bool(info.get("is_local", False))
        if disk.get("disk_type") and disk.get("capacity_gb") is not None:
            disk["disk_name"] = "{}_{}".format(disk["disk_type"], disk["capacity_gb"])

    def run_flow(self):
        """主流程入口"""
        self._validate()
        self._enrich_hosts_disks_from_merged_storage()
        self._validate_disk_identity_after_enrich()

        pipeline = Builder(root_id=self.root_id, data=self.data)
        # 每台机器一个子流程, 机器间并发
        sub_pipelines = []
        for host in self.data["hosts"]:
            sub_data = copy.deepcopy(self.data)
            # 每个子流程的 ticket_data 不带全量 hosts, 避免 actuator 误用
            sub_data["hosts"] = [host]
            sub_pipeline = self._build_host_sub_pipeline(host, sub_data)
            sub_pipelines.append(sub_pipeline)

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline(init_trans_data_class=DiskBenchmarkContext(), is_drop_random_user=False)

    def _build_host_sub_pipeline(self, host: Dict, sub_data: Dict):
        """
        单台机器子流程：先做空闲检查, 再对该机的多块盘串行跑 actuator + 写库
        机器内部串行是为了避免同机多盘并发互相争抢 IO, 让每块盘的测量数字更准
        """
        ip = host["ip"]
        bk_cloud_id = host.get("bk_cloud_id", self.data.get("bk_cloud_id", 0))

        sub = SubBuilder(root_id=self.root_id, data=sub_data)

        # 1) 机器层空闲检查 (走 SOPs 模板)
        sub.add_act(
            act_name=_("执行sa空闲检查 ({})").format(ip),
            act_component_code=CheckMachineIdleComponent.code,
            kwargs=asdict(
                InitCheckForResourceKwargs(
                    ips=[ip],
                    bk_biz_id=self.data.get("bk_biz_id"),
                    strict_idle_check=bool(self.data.get("strict_idle_check", False)),
                )
            ),
        )

        # 2) 下发 dbactuator 介质到目标机 /data/install/dbactuator
        # 通用主机不一定经过资源池初始化流程, 不能假设 actuator_template 里写的 cp 源文件已存在
        # 走标准 TransFileComponent + GetFileList 链路, 拉 Package 表里 mysql 类型的最新 actuator
        sub.add_act(
            act_name=_("下发 dbactuator 介质 ({})").format(ip),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=bk_cloud_id,
                    exec_ip=ip,
                    file_list=GetFileList(db_type=DBType.MySQL.value).get_db_actuator_package(),
                )
            ),
        )

        # 3) 多盘串行: 跑 actuator -> 写库
        for disk in host["disks"]:
            self._add_disk_acts(sub, ip, bk_cloud_id, disk)

        return sub.build_sub_process(sub_name=_("主机 {} 磁盘性能基线采集").format(ip))

    def _add_disk_acts(self, sub: SubBuilder, ip: str, bk_cloud_id: int, disk: Dict):
        """对一块盘添加 [actuator 跑压测 -> 解析输出写 BaselineDisk] 两个串行 act"""
        target = disk["target"]
        disk_name = disk["disk_name"]

        # 2.1) actuator 跑压测, 把结果按 <ctx>...</ctx> 输出
        sub.add_act(
            act_name=_("dbactuator 跑磁盘压测 [{} disk={} target={}]").format(ip, disk_name, target),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs={
                **asdict(
                    ExecActuatorKwargs(
                        bk_cloud_id=bk_cloud_id,
                        run_as_system_user=DBA_ROOT_USER,
                        job_timeout=LONG_JOB_TIMEOUT,
                        payload_class="{}.{}".format(OSActPayload.__module__, OSActPayload.__name__),
                        get_mysql_payload_func=OSActPayload.get_disk_benchmark_payload.__name__,
                    )
                ),
                "exec_ip": ip,
                "component_kwargs": {
                    "target": target,
                    # actuator(dbactuator os disk-benchmark) 端 extend.size 固定, 入参用语义更明确的 test_file_size 映射过来
                    "size": disk.get("test_file_size", self.data.get("test_file_size", "8G")),
                    "runtime": disk.get("runtime", self.data.get("runtime", 30)),
                    "jobs": disk.get("jobs", self.data.get("jobs", 64)),
                    "throughput_jobs": disk.get("throughput_jobs", self.data.get("throughput_jobs", 16)),
                },
            },
            write_payload_var="benchmark_result",
        )

        # 2.2) 解析 trans_data.benchmark_result 写 BaselineDisk
        # 防御深度: 仅在 ENABLE_DBM_AI=true 时挂这个节点。
        # 关闭时的行为:
        #   - flow 仍能跑通 (空闲检查 + 下发 actuator + 跑压测), 但跳过写库
        #   - 测试结果只在 dbactuator 节点的 stdout (含 <ctx>...</ctx> JSON) 中可见
        #   - 适合临时 ad-hoc 性能测量; 长期基线采集仍需开 ENABLE_DBM_AI
        # 这里用构建期 if 跳过整个节点, 流程详情图上不会出现该节点, 比建空节点更简洁
        if not env.ENABLE_DBM_AI:
            logger.info(
                _(
                    "ENABLE_DBM_AI=false, 跳过写入 BaselineDisk 节点 [host={} disk={} target={}]; 结果仅在 actuator 节点 stdout 中可见"
                ).format(ip, disk_name, target)
            )
            return

        sub.add_act(
            act_name=_("写入 BaselineDisk [disk_name={}]").format(disk_name),
            act_component_code=BaselineDiskWriteComponent.code,
            kwargs={
                "disk_name": disk_name,
                "disk_type": disk.get("disk_type"),
                "disk_model": "",
                "is_local": disk.get("is_local"),
                "capacity_gb": disk.get("capacity_gb"),
            },
        )
