# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

历史机器字段回填:
1. storage_device(磁盘块设备信息): 综合 资源池 cvm 详情接口(拿 disk_id 对应的云盘类型/容量) +
   远程脚本(df + /sys/block 拿挂载点对应的设备和 disk_id), 合并后批量回填 Machine.storage_device。
2. cloud_inst_id(云主机实例 ID): 从 CMDB 的 bk_cloud_inst_id 字段回填 Machine.cloud_inst_id。

注: 两个回填入口均接收一批 Machine, 由调用方决定范围并自行分批(建议单批数百台内)。

storage_device 数据格式示例:
    {"/data": {"size": 100, "disk_id": "disk-xxx", "disk_type": "CLOUD_PREMIUM", "file_type": "ext4"}}
    IT 开头机型本地盘: {"/data": {"size": 3301, "disk_id": "", "disk_type": "nvme_ssd", "file_type": "ext3"}}
"""
import logging
import time
from collections import defaultdict
from typing import Dict, List

from django.utils.translation import gettext as _

from backend import env
from backend.components import CCApi, JobApi
from backend.components.dbresource.client import DBResourceApi
from backend.db_meta import api
from backend.flow.consts import DBA_ROOT_USER
from backend.utils.string import base64_encode

logger = logging.getLogger("root")

# 轮询 Job 状态的参数
JOB_POLL_INTERVAL = 5  # 秒
JOB_POLL_MAX_RETRIES = 60  # 最多轮询 60 次, 即 5 分钟

# 数据盘挂载点匹配规则: /data, /data1, /data2, /data3 ... (与项目约定一致, storage_device 为数据盘)
DATA_MOUNT_POINT_PATTERN = "^/data[0-9]*$"

# 脚本输出行的 sentinel 前缀, 用于在 Job 日志噪音中精准提取采集结果
STORAGE_DEVICE_SENTINEL = "STORAGE_DEVICE"

# disk_type 存 cvm 返回的原生云盘类型(不做 SSD/HDD 映射), 取值含义:
#   CLOUD_PREMIUM : 高性能云硬盘
#   CLOUD_BSSD    : 通用型 SSD 云硬盘
#   CLOUD_SSD     : SSD 云硬盘
#   CLOUD_HSSD    : 增强型 SSD 云硬盘
#   CLOUD_TSSD    : 极速型 SSD 云硬盘
#   SSD      : IT 开头机型上的本地NVMe SSD(无云盘 disk_id, 由机型规则补全 disk_type)

# IT 开头标准设备类型(如 IT3c.4XLARGE32) 为本地盘, 无 CVM 云盘 disk_id, 统一录入 disk_type
IT_LOCAL_SSD_DISK_TYPE = "SSD"

# 远程采集脚本: 动态发现所有 /dataN 数据盘挂载点, 逐个输出 "挂载点|设备|disk_id|文件系统|容量GB"
DISK_COLLECT_SCRIPT = """#!/bin/sh
for mp in $(df -P 2>/dev/null | awk 'NR>1{{print $NF}}' | grep -E '{mount_pattern}'); do
    dev=$(df -P "$mp" 2>/dev/null | awk 'NR==2{{print $1}}')
    [ -z "$dev" ] && continue
    fstype=$(df -PT "$mp" 2>/dev/null | awk 'NR==2{{print $2}}')
    size=$(df -P -BG "$mp" 2>/dev/null | awk 'NR==2{{gsub("G","",$2); print $2}}')
    base=$(basename "$dev" | sed 's/[0-9]*$//')
    serial=$(cat /sys/block/$base/serial 2>/dev/null)
    echo "{sentinel}|$mp|$dev|$serial|$fstype|$size"
done
""".format(
    mount_pattern=DATA_MOUNT_POINT_PATTERN, sentinel=STORAGE_DEVICE_SENTINEL
)


def _query_cvm_disk_map(ips: List[str]) -> Dict[str, Dict[str, dict]]:
    """
    查询 cvm 详情, 返回 {ip: {disk_id: {"DiskType": ..., "DiskSize": ...}}}
    disk_type 存云盘原始值(如 CLOUD_PREMIUM), 不做映射
    """
    if not ips:
        return {}
    try:
        data = DBResourceApi.resource_cvm_detail({"ips": ips}) or {}
    except Exception as e:  # noqa
        logger.warning(_("查询 cvm 详情失败: {}").format(str(e)))
        return {}

    cvm_map: Dict[str, Dict[str, dict]] = {}
    for ip, detail in data.items():
        cvm_map[ip] = {
            disk["DiskId"]: {"DiskType": disk.get("DiskType", ""), "DiskSize": disk.get("DiskSize", 0)}
            for disk in (detail.get("datadiskList") or [])
            if disk.get("DiskId")
        }
    return cvm_map


def _exec_disk_collect_script(target_ips: List[dict]) -> Dict[str, str]:
    """
    在目标机器上同步执行采集脚本, 返回 {ip: log_content}
    target_ips: [{"ip": "127.0.0.1", "bk_cloud_id": 0}]
    """
    body = {
        "bk_scope_type": "biz_set",
        "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
        "account_alias": DBA_ROOT_USER,
        "task_name": _("DBM 采集主机磁盘块设备信息"),
        "script_content": base64_encode(DISK_COLLECT_SCRIPT),
        "script_language": 1,
        "target_server": {"ip_list": target_ips},
        "timeout": 300,
    }
    job_task = JobApi.fast_execute_script(body, use_admin=True)
    job_instance_id = job_task["job_instance_id"]

    for __ in range(JOB_POLL_MAX_RETRIES):
        ip_logs = _fetch_job_ip_logs(job_instance_id)
        if ip_logs is not None:
            return ip_logs
        time.sleep(JOB_POLL_INTERVAL)

    raise Exception(_("采集主机磁盘块设备信息超时, job_instance_id: {}").format(job_instance_id))


def _fetch_job_ip_logs(job_instance_id: int):
    """
    查询 job 执行状态, 完成则返回 {ip: log_content}, 未完成返回 None
    """
    status_resp = JobApi.get_job_instance_status(
        {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "job_instance_id": job_instance_id,
            "return_ip_result": True,
        },
        use_admin=True,
    )
    if not status_resp["finished"]:
        return None

    step_instance = status_resp["step_instance_list"][0]
    step_instance_id = step_instance["step_instance_id"]
    ip_result_list = step_instance["step_ip_result_list"]
    host_id_to_ip = {res["bk_host_id"]: res["ip"] for res in ip_result_list}

    log_resp = JobApi.batch_get_job_instance_ip_log(
        {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "job_instance_id": job_instance_id,
            "step_instance_id": step_instance_id,
            "host_id_list": list(host_id_to_ip.keys()),
        },
        use_admin=True,
    )
    ip_logs: Dict[str, str] = {}
    for log in log_resp.get("script_task_logs") or []:
        ip = log.get("ip") or host_id_to_ip.get(log.get("host_id"))
        if ip:
            ip_logs[ip] = log.get("log_content", "")
    return ip_logs


def _is_it_local_disk_device_class(bk_svr_device_cls_name: str) -> bool:
    """标准设备类型以 IT 开头时为本地盘机型(无云盘 disk_id)."""
    name = (bk_svr_device_cls_name or "").strip().upper()
    return bool(name) and name.startswith("IT")


def _build_storage_device(log_content: str, cvm_disk_map: Dict[str, dict], bk_svr_device_cls_name: str = "") -> dict:
    """
    解析单台机器的采集脚本输出, 合并 cvm 的云盘类型, 生成 storage_device
    cvm_disk_map: {disk_id: {"DiskType": ..., "DiskSize": ...}}
    bk_svr_device_cls_name: CMDB 标准设备类型; IT 开头机型为本地 SSD, disk_type 固定为 nvme_ssd
    """
    storage_device: dict = {}
    for line in (log_content or "").splitlines():
        line = line.strip()
        if not line.startswith(STORAGE_DEVICE_SENTINEL + "|"):
            continue
        parts = line.split("|")
        if len(parts) != 6:
            continue
        __, mount_point, device, disk_id, file_type, size = parts
        cvm_info = cvm_disk_map.get(disk_id, {})
        disk_type = cvm_info.get("DiskType", "")  # 云盘原始值, 不映射
        if _is_it_local_disk_device_class(bk_svr_device_cls_name):
            disk_type = IT_LOCAL_SSD_DISK_TYPE
        storage_device[mount_point] = {
            "size": int(size) if size.isdigit() else cvm_info.get("DiskSize", 0),
            "disk_id": disk_id,
            "disk_type": disk_type,
            "file_type": file_type,
        }
    return storage_device


def fill_machine_storage_device(machines) -> Dict[str, dict]:
    """
    综合 cvm 详情 + 远程脚本, 回填一批 machine 的 storage_device。

    @param machines: Machine 实例的列表/queryset(调用方决定范围, 例如 storage_device 为空的机器)
    @return: 实际更新的 {ip: storage_device} 统计
    """
    # 收集 ip, 并按云区域分组(cvm 查询只需 ip, JOB 下发与写库需按 bk_cloud_id)
    all_ips: List[str] = []
    cloud_to_targets: Dict[int, List[dict]] = defaultdict(list)
    for machine in machines:
        all_ips.append(machine.ip)
        cloud_to_targets[machine.bk_cloud_id].append({"ip": machine.ip, "bk_cloud_id": machine.bk_cloud_id})

    if not all_ips:
        logger.info(_("没有需要回填磁盘块设备信息的主机"))
        return {}

    # 查询 cvm 磁盘类型信息
    cvm_disk_map = _query_cvm_disk_map(all_ips)

    ip_to_device_cls = {m.ip: (getattr(m, "bk_svr_device_cls_name", None) or "") for m in machines}

    updated: Dict[str, dict] = {}
    for bk_cloud_id, target_ips in cloud_to_targets.items():
        # 单个云区域失败(JOB 超时/接口异常)不影响其他云区域的回填
        try:
            ip_logs = _exec_disk_collect_script(target_ips)
            update_machines = []
            for ip, log_content in ip_logs.items():
                storage_device = _build_storage_device(
                    log_content, cvm_disk_map.get(ip, {}), ip_to_device_cls.get(ip, "")
                )
                if storage_device:
                    update_machines.append({"ip": ip, "storage_device": storage_device})
                    updated[ip] = storage_device

            if update_machines:
                api.machine.update_storage_device(bk_cloud_id=bk_cloud_id, machines=update_machines)
                logger.info(_("云区域 {} 回填磁盘块设备信息成功, 共 {} 台").format(bk_cloud_id, len(update_machines)))
        except Exception as e:  # noqa
            logger.exception(_("云区域 {} 回填磁盘块设备信息失败: {}").format(bk_cloud_id, str(e)))
            continue

    return updated


def fill_machine_cloud_inst_id(machines) -> Dict[str, str]:
    """
    从 CMDB 回填一批 machine 的 cloud_inst_id(云主机实例 ID, 即 CMDB 的 bk_cloud_inst_id)。

    @param machines: Machine 实例的列表/queryset(调用方决定范围, 例如 cloud_inst_id 为空的机器)
    @return: 实际更新的 {ip: cloud_inst_id} 统计
    """
    host_id_to_machine = {machine.bk_host_id: machine for machine in machines}
    if not host_id_to_machine:
        logger.info(_("没有需要回填云主机实例 ID 的主机"))
        return {}

    host_infos = CCApi.list_hosts_without_biz(
        {
            "fields": ["bk_host_id", "bk_cloud_inst_id"],
            "host_property_filter": {
                "condition": "AND",
                "rules": [{"field": "bk_host_id", "operator": "in", "value": list(host_id_to_machine.keys())}],
            },
        },
        use_admin=True,
    ).get("info", [])

    # 按云区域分组写库
    cloud_to_machines: Dict[int, List[dict]] = defaultdict(list)
    updated: Dict[str, str] = {}
    for host in host_infos:
        cloud_inst_id = host.get("bk_cloud_inst_id") or ""
        machine = host_id_to_machine.get(host["bk_host_id"])
        if not cloud_inst_id or not machine:
            continue
        cloud_to_machines[machine.bk_cloud_id].append({"ip": machine.ip, "cloud_inst_id": cloud_inst_id})
        updated[machine.ip] = cloud_inst_id

    for bk_cloud_id, update_machines in cloud_to_machines.items():
        api.machine.update_cloud_inst_id(bk_cloud_id=bk_cloud_id, machines=update_machines)
        logger.info(_("云区域 {} 回填云主机实例 ID 成功, 共 {} 台").format(bk_cloud_id, len(update_machines)))

    return updated
