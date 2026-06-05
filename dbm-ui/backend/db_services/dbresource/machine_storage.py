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
   另提供 fetch_merged_storage_device_for_hosts(hosts: List[dict]) 供流程编排侧按 ip 拉取合并视图(不写库)。

storage_device 数据格式示例:
    {"/data": {"size": 100, "disk_id": "disk-xxx", "disk_type": "CLOUD_PREMIUM", "file_type": "ext4", "is_local": false}}
    NVMe 直通本地盘(CVM LOCAL_NVME):
    {"/data": {"size": 3570, "disk_id": "ldisk-xxx", "disk_type": "NVME_SSD", "file_type": "ext4", "is_local": true}}
"""
import logging
import re
import time
from collections import defaultdict
from typing import Dict, List, Tuple

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

# disk_type 以 CVM 为权威源; CLOUD_* 存 CVM 原始值, LOCAL_NVME 映射为 NVME_SSD:
#   CLOUD_PREMIUM / CLOUD_BSSD / CLOUD_SSD / CLOUD_HSSD / CLOUD_TSSD : 云盘
#   LOCAL_NVME -> NVME_SSD (CVM 本地 NVMe 直通盘, DiskId 常为 ldisk- 前缀)
# 对不上 CVM 时云盘 disk_type 留空; 本地盘可由 /dev/nvme*、ldisk-、LOCAL_*、IT 机型推断为 NVME_SSD

# CVM LOCAL_NVME 映射为 BaselineDisk 等模块使用的 NVME_SSD
IT_LOCAL_SSD_DISK_TYPE = "NVME_SSD"


def _resolve_sysfs_block_base(device: str) -> str:
    """
    从块设备路径解析 /sys/block/<base>/serial 所需的 base 名.

    - 传统盘分区: /dev/vda1 -> vda, /dev/sdb2 -> sdb
    - NVMe 分区: /dev/nvme0n1p1 -> nvme0n1 (不能仅用 sed 去尾数字, 否则会得到 nvme0n1p)
    - NVMe 整盘: /dev/nvme0n1 -> nvme0n1 (同理不能去尾数字, 否则会得到 nvme0n)
    """
    base = (device or "").strip().rsplit("/", 1)[-1]
    if not base:
        return ""
    nvme_match = re.match(r"^(nvme\d+n\d+)(?:p\d+)?$", base, re.IGNORECASE)
    if nvme_match:
        return nvme_match.group(1)
    i = len(base)
    while i > 0 and base[i - 1].isdigit():
        i -= 1
    return base[:i] if i > 0 else base


def _parse_size_gb(size_str: str) -> int:
    """解析 df 容量字符串为 GB 整数, 支持纯数字、G、T 后缀."""
    s = (size_str or "").strip()
    if not s:
        return 0
    if s.isdigit():
        return int(s)
    upper = s.upper()
    try:
        if upper.endswith("T"):
            return int(float(upper[:-1]) * 1024)
        if upper.endswith("G"):
            return int(float(upper[:-1]))
    except ValueError:
        pass
    return 0


# 远程采集脚本: 动态发现所有 /dataN 数据盘挂载点, 逐个输出 "挂载点|设备|disk_id|文件系统|容量GB"
DISK_COLLECT_SCRIPT = """#!/bin/sh
for mp in $(df -P 2>/dev/null | awk 'NR>1{{print $NF}}' | grep -E '{mount_pattern}'); do
    dev=$(df -P "$mp" 2>/dev/null | awk 'NR==2{{print $1}}')
    [ -z "$dev" ] && continue
    fstype=$(df -PT "$mp" 2>/dev/null | awk 'NR==2{{print $2}}')
    size=$(df -P -BG "$mp" 2>/dev/null | awk 'NR==2{{gsub("G","",$2); print $2}}')
    base=$(basename "$dev")
    case "$base" in
      nvme*n*p*)
        base=$(echo "$base" | sed 's/p[0-9]*$//')
        ;;
      nvme*n*)
        ;;
      *)
        base=$(echo "$base" | sed 's/[0-9]*$//')
        ;;
    esac
    serial=$(cat /sys/block/$base/serial 2>/dev/null)
    echo "{sentinel}|$mp|$dev|$serial|$fstype|$size"
done
""".format(
    mount_pattern=DATA_MOUNT_POINT_PATTERN, sentinel=STORAGE_DEVICE_SENTINEL
)


def _query_cvm_disk_map(ips: List[str]) -> Dict[str, dict]:
    """
    查询 cvm 详情, 返回 {ip: {"disks": {disk_id: {"DiskType", "DiskSize"}}, "instance_type": str}}
    - disks: 数据盘信息, DiskType 存云盘原始值(如 CLOUD_PREMIUM), 不做映射
    - instance_type: 云厂商机型(如 SA2.MEDIUM4), 与 CMDB bk_svr_device_cls_name 等价, 用于 IT 本地盘机型兜底判定
    """
    if not ips:
        return {}
    try:
        data = DBResourceApi.resource_cvm_detail({"ips": ips}) or {}
    except Exception as e:  # noqa
        logger.warning(_("查询 cvm 详情失败: {}").format(str(e)))
        return {}

    cvm_map: Dict[str, dict] = {}
    for ip, detail in data.items():
        cvm_map[ip] = {
            "disks": {
                disk["DiskId"]: {"DiskType": disk.get("DiskType", ""), "DiskSize": disk.get("DiskSize", 0)}
                for disk in (detail.get("datadiskList") or [])
                if disk.get("DiskId")
            },
            "instance_type": detail.get("instanceType") or "",
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
    """标准设备类型以 IT 开头时为本地盘机型."""
    name = (bk_svr_device_cls_name or "").strip().upper()
    return bool(name) and name.startswith("IT")


def _is_nvme_passthrough_disk(device: str) -> bool:
    """子机内设备名为 /dev/nvme* 即直通本地盘(读不到 serial, serial 对不上 CVM DiskId)."""
    return (device or "").strip().lower().startswith("/dev/nvme")


def _normalize_disk_type(cvm_disk_type: str) -> str:
    """CVM 本地 NVMe 盘类型 LOCAL_NVME 映射为 NVME_SSD; 其余(CLOUD_*) 原值不映射."""
    if (cvm_disk_type or "").strip().upper() == "LOCAL_NVME":
        return IT_LOCAL_SSD_DISK_TYPE
    return cvm_disk_type or ""


def _is_local_disk(cvm_disk_type: str, cvm_disk_id: str, device: str, it_machine_local: bool) -> bool:
    """本地盘判定(满足其一): CVM 类型 LOCAL_* / DiskId ldisk- / 设备名 /dev/nvme* / IT 机型."""
    if (cvm_disk_type or "").strip().upper().startswith("LOCAL"):
        return True
    if (cvm_disk_id or "").startswith("ldisk-"):
        return True
    if _is_nvme_passthrough_disk(device):
        return True
    return it_machine_local


def _parse_collect_log(log_content: str) -> List[dict]:
    """解析采集脚本 sentinel 行, 返回 shell 盘列表(保序)."""
    shell_disks: List[dict] = []
    for line in (log_content or "").splitlines():
        line = line.strip()
        if not line.startswith(STORAGE_DEVICE_SENTINEL + "|"):
            continue
        parts = line.split("|")
        if len(parts) != 6:
            continue
        __, mount_point, device, serial, file_type, size = parts
        shell_disks.append(
            {
                "mount_point": mount_point,
                "device": device,
                "serial": (serial or "").strip(),
                "file_type": file_type,
                "size_gb": _parse_size_gb(size),
            }
        )
    return shell_disks


def _capacity_within_tolerance(cvm_gb: int, script_gb: int) -> bool:
    """df 容量与 CVM DiskSize 是否在容差内: max(50GB, 20%)."""
    if cvm_gb <= 0 or script_gb <= 0:
        return False
    diff = abs(cvm_gb - script_gb)
    threshold = max(50, int(0.2 * max(cvm_gb, script_gb)))
    return diff <= threshold


def _match_remaining_cvm_disks(
    remaining_shell: List[dict], remaining_cvm: Dict[str, dict]
) -> Dict[int, Tuple[str, dict]]:
    """
    剩余 shell 盘与剩余 CVM 盘配对: 两边各剩 1 块则直取, 否则按容量就近(容差内).
    返回 id(shell_disk) -> (cvm_disk_id, cvm_info)
    """
    if not remaining_shell or not remaining_cvm:
        return {}
    cvm_items = list(remaining_cvm.items())
    if len(remaining_shell) == 1 and len(cvm_items) == 1:
        sd = remaining_shell[0]
        cvm_disk_id, cvm_info = cvm_items[0]
        return {id(sd): (cvm_disk_id, cvm_info)}

    result: Dict[int, Tuple[str, dict]] = {}
    used_cvm_ids: set = set()
    for sd in remaining_shell:
        script_gb = sd.get("size_gb") or 0
        best_id = None
        best_info = None
        best_diff = None
        for cvm_disk_id, cvm_info in cvm_items:
            if cvm_disk_id in used_cvm_ids:
                continue
            try:
                cvm_gb = int(cvm_info.get("DiskSize") or 0)
            except (TypeError, ValueError):
                cvm_gb = 0
            if not _capacity_within_tolerance(cvm_gb, script_gb):
                continue
            diff = abs(cvm_gb - script_gb)
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best_id = cvm_disk_id
                best_info = cvm_info
        if best_id is not None and best_info is not None:
            result[id(sd)] = (best_id, best_info)
            used_cvm_ids.add(best_id)
    return result


def _resolve_disk_size_gb(script_gb: int, cvm_info: dict) -> int:
    """容量 GB: 优先 CVM DiskSize, 否则用脚本 df 值."""
    cvm_gb = cvm_info.get("DiskSize")
    if cvm_gb is not None:
        try:
            return int(cvm_gb)
        except (TypeError, ValueError):
            pass
    return script_gb


def _pair_shell_disks_to_cvm(shell_disks: List[dict], cvm_disk_map: Dict[str, dict]) -> Dict[int, Tuple[str, dict]]:
    """serial 精确匹配 -> 剩余单盘/按容量配对."""
    shell_to_cvm: Dict[int, Tuple[str, dict]] = {}
    used_cvm_ids: set = set()
    for sd in shell_disks:
        serial = sd.get("serial") or ""
        if serial and serial in cvm_disk_map:
            shell_to_cvm[id(sd)] = (serial, cvm_disk_map[serial])
            used_cvm_ids.add(serial)
    remaining_shell = [sd for sd in shell_disks if id(sd) not in shell_to_cvm]
    remaining_cvm = {k: v for k, v in cvm_disk_map.items() if k not in used_cvm_ids}
    shell_to_cvm.update(_match_remaining_cvm_disks(remaining_shell, remaining_cvm))
    return shell_to_cvm


def _resolve_disk_type(cvm_disk_type: str, cvm_disk_id: str, device: str, it_machine_local: bool) -> str:
    """
    解析 disk_type.

    /dev/nvme* 设备恒为 NVME_SSD(直通本地 SSD, 优先于 CVM 配对结果, 避免容量误配成 CLOUD_*).
    其余: CVM 优先; 本地盘(CVM LOCAL_* / ldisk- / IT 机型)兜底 NVME_SSD.
    """
    if _is_nvme_passthrough_disk(device):
        return IT_LOCAL_SSD_DISK_TYPE
    disk_type = _normalize_disk_type(cvm_disk_type)
    if disk_type:
        return disk_type
    if _is_local_disk(cvm_disk_type, cvm_disk_id, device, it_machine_local):
        return IT_LOCAL_SSD_DISK_TYPE
    return ""


def _assemble_storage_entry(sd: dict, cvm_match: Tuple[str, dict], it_machine_local: bool) -> dict:
    """组装单挂载点的 storage_device 条目."""
    device = sd.get("device", "")
    if cvm_match:
        cvm_disk_id, cvm_info = cvm_match
        raw_type = cvm_info.get("DiskType", "")
        is_local = _is_local_disk(raw_type, cvm_disk_id, device, it_machine_local)
        return {
            "size": _resolve_disk_size_gb(sd.get("size_gb") or 0, cvm_info),
            "disk_id": cvm_disk_id,
            "disk_type": _resolve_disk_type(raw_type, cvm_disk_id, device, it_machine_local),
            "file_type": sd.get("file_type", ""),
            "is_local": is_local,
        }
    serial = sd.get("serial") or ""
    is_local = _is_local_disk("", serial, device, it_machine_local)
    return {
        "size": sd.get("size_gb") or 0,
        "disk_id": serial,
        "disk_type": _resolve_disk_type("", serial, device, it_machine_local),
        "file_type": sd.get("file_type", ""),
        "is_local": is_local,
    }


def _build_storage_device(
    log_content: str, cvm_disk_map: Dict[str, dict], bk_svr_device_cls_name: str = "", cvm_instance_type: str = ""
) -> dict:
    """
    以 CVM datadiskList 为权威源, 合并 shell 采集结果生成 storage_device.

    配对: serial == CVM DiskId -> 剩余单盘直取 -> 按容量就近(max(50GB, 20%)).
    对不上 CVM 时以 shell 为准(disk_id=serial 可能空); 本地盘 disk_type 兜底 NVME_SSD, 云盘留空.
    disk_type: CVM LOCAL_NVME 映射 NVME_SSD, CLOUD_* 原值; 容量优先 CVM DiskSize.
    is_local: CVM LOCAL_* / ldisk- / /dev/nvme* / IT 机型(满足其一).
    """
    shell_disks = _parse_collect_log(log_content)
    if not shell_disks:
        return {}
    it_machine_local = _is_it_local_disk_device_class(bk_svr_device_cls_name or cvm_instance_type)
    shell_to_cvm = _pair_shell_disks_to_cvm(shell_disks, cvm_disk_map)
    storage_device: dict = {}
    for sd in shell_disks:
        mount_point = sd["mount_point"]
        storage_device[mount_point] = _assemble_storage_entry(sd, shell_to_cvm.get(id(sd)), it_machine_local)
    return storage_device


def fetch_merged_storage_device_for_hosts(hosts: List[dict]) -> Dict[str, Dict[str, dict]]:
    """
    综合资源池 CVM 详情 + Job 采集脚本, 得到各主机合并后的 storage_device 视图, 不写库。
    合并逻辑与 fill_machine_storage_device 一致, 供其它流程(如磁盘基线压测)在编排前取数。

    @param hosts: 每项须含 ip、bk_cloud_id；可选 bk_svr_device_cls_name(不传时 IT 机型判定由 CVM instanceType 兜底)
    @return: {ip: storage_device}; 某台采集失败或为空则该 ip 不出现在结果中
    """
    if not hosts:
        return {}
    all_ips: List[str] = []
    cloud_to_targets: Dict[int, List[dict]] = defaultdict(list)
    for h in hosts:
        ip = h.get("ip")
        if not ip:
            continue
        all_ips.append(ip)
        bk_cloud_id = int(h.get("bk_cloud_id", 0))
        cloud_to_targets[bk_cloud_id].append({"ip": ip, "bk_cloud_id": bk_cloud_id})

    if not all_ips:
        return {}

    cvm_disk_map = _query_cvm_disk_map(all_ips)
    ip_to_device_cls = {h["ip"]: (h.get("bk_svr_device_cls_name") or "") for h in hosts if h.get("ip")}

    merged: Dict[str, Dict[str, dict]] = {}
    for bk_cloud_id, target_ips in cloud_to_targets.items():
        try:
            ip_logs = _exec_disk_collect_script(target_ips)
            for ip, log_content in ip_logs.items():
                cvm_entry = cvm_disk_map.get(ip, {})
                storage_device = _build_storage_device(
                    log_content,
                    cvm_entry.get("disks", {}),
                    ip_to_device_cls.get(ip, ""),
                    cvm_entry.get("instance_type", ""),
                )
                if storage_device:
                    merged[ip] = storage_device
        except Exception as e:  # noqa
            logger.warning(_("获取主机合并磁盘信息失败 cloud_id={} {}").format(bk_cloud_id, str(e)))
            continue

    return merged


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
                cvm_entry = cvm_disk_map.get(ip, {})
                storage_device = _build_storage_device(
                    log_content,
                    cvm_entry.get("disks", {}),
                    ip_to_device_cls.get(ip, ""),
                    cvm_entry.get("instance_type", ""),
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
