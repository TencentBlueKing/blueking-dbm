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
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from django.utils.translation import gettext as _

from backend import env
from backend.components import BKMonitorV3Api, JobApi
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.common.impl.job import get_job_exec_status
from backend.flow.consts import DBA_ROOT_USER
from backend.utils.string import base64_encode
from backend.utils.time import timezone2timestamp

logger = logging.getLogger("flow")

# dbactuator 运行目录模板，uid = ticket_id（渲染值见 flow/utils/kafka/script_template.py 里的 {{uid}}）
DBACTUATOR_INSTALL_DIR_TPL = "/data/install/dbactuator-{uid}"
THROTTLE_FILE_NAME = "throttle_rate.txt"
PROGRESS_FILE_NAME = "progress.json"
# 调速模式标记文件，人工设置限速(kafka_rebalance_control_set_throttle)后写"manual"，sidecar据此
# 跳过自动调速，避免刚设置的值被下一轮自动逻辑立刻覆盖回去；不存在时约定为"auto"（默认自动模式）
OVERRIDE_FILE_NAME = "throttle_override.txt"
VALID_OVERRIDE_MODES = ("auto", "manual")

# 自动调速参数：初始限速100MB/s，下限50MB/s，每次调整step为50MB/s。
# 上限不能写死字节数——不同规格集群broker带宽差异很大（1.5Gbps~10Gbps+），固定值对小规格集群可能
# 形同虚设（甚至超过物理带宽本身，等于没有上限保护），对大规格集群又会限制本可以更快完成的场景。
# 改成动态：取参与rebalance的broker中实测带宽最小值的MAX_THROTTLE_BANDWIDTH_RATIO，
# 留30%给客户端正常生产消费流量
INITIAL_THROTTLE_BYTES_PER_SEC = 100 * 1024 * 1024
MIN_THROTTLE_BYTES_PER_SEC = 50 * 1024 * 1024
MAX_THROTTLE_BANDWIDTH_RATIO = 0.7
STEP_BYTES_PER_SEC = 50 * 1024 * 1024
HIGH_WATERMARK_PCT = 85
LOW_WATERMARK_PCT = 80
# 人工设置限速时，若监控数据暂时不可用（拿不到动态上限），退化用这个绝对值兜底——
# 只用来拦截明显异常的输入（比如误填单位导致数值离谱），不代表任何真实带宽含义
ABSOLUTE_MAX_THROTTLE_BYTES_PER_SEC = 2 * 1024 * 1024 * 1024

JOB_POLL_INTERVAL = 3
JOB_POLL_MAX_RETRIES = 20  # 读写小文件的脚本，20次*3s=60s足够


def _run_remote_script(ip: str, bk_cloud_id: int, script: str, task_name: str, timeout: int = 60) -> str:
    """
    在目标机器上远程执行一段shell脚本并返回标准输出，复用kafka_toolbox.py的JobApi调用模式
    """
    body = {
        "account_alias": DBA_ROOT_USER,
        "bk_scope_type": "biz_set",
        "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
        "task_name": task_name,
        "script_content": base64_encode(script),
        "script_language": 1,
        "target_server": {"ip_list": [{"ip": ip, "bk_cloud_id": bk_cloud_id}]},
        "timeout": timeout,
    }
    job_task = JobApi.fast_execute_script(body, use_admin=True)

    job_instance_id = job_task["job_instance_id"]
    for _i in range(JOB_POLL_MAX_RETRIES):
        job_resp = get_job_exec_status(job_instance_id)
        if job_resp["finished"]:
            log_content_parts = [
                log_entry["log_content"] for log_entry in job_resp["job_log_resp"] if log_entry.get("log_content")
            ]
            return "\n".join(log_content_parts)
        time.sleep(JOB_POLL_INTERVAL)

    raise Exception(_("远程执行脚本超时: {}").format(task_name))


_FILE_NOT_FOUND_MARKER = "__FILE_NOT_FOUND__"
_FILE_READ_ERROR_MARKER = "__FILE_READ_ERROR__"
_STATE_DELIMITER = "___STATE___"


def _read_file_snippet(path: str) -> str:
    """
    生成读取单个远程文件的shell片段，区分"文件不存在"和"文件存在但读取失败"（权限/磁盘异常等）——
    两者语义完全不同：前者是rebalance还没跑到写文件的正常阶段，后者是需要报警的基础设施故障，
    混在一起会让权限错误、目录不可访问这类真实故障被静默当成"还没生成"。
    """
    return (
        f'if [ ! -e "{path}" ]; then echo "{_FILE_NOT_FOUND_MARKER}"; '
        f'else _content=$(cat "{path}" 2>/dev/null) && echo "$_content" || echo "{_FILE_READ_ERROR_MARKER}"; fi'
    )


def _parse_file_part(raw: str, file_desc: str) -> Optional[str]:
    raw = raw.strip()
    if raw == _FILE_READ_ERROR_MARKER:
        raise Exception(_("远程读取{}失败（权限或磁盘异常），请检查执行节点状态").format(file_desc))
    if not raw or raw == _FILE_NOT_FOUND_MARKER:
        return None
    return raw


def read_rebalance_state(ip: str, bk_cloud_id: int, ticket_id: int) -> Dict[str, Optional[str]]:
    """
    一次远程脚本执行同时读取progress.json、throttle_rate.txt、throttle_override.txt三个文件，
    避免每轮拆成多次Job调用。sidecar每2分钟一轮，拆成多次独立Job轮询（各自最多60s）会明显拖慢
    单轮检查耗时、加重Job平台压力，合并成一次脚本后只需一次Job往返。
    progress/throttle_rate缺失的返回None（文件不存在，不视为错误）；文件存在但读取失败会抛异常
    （不能跟"文件不存在"混为一谈，那样会把权限/磁盘异常静默当成"还没生成"）。
    override_mode缺失时归一化为"auto"（默认自动模式，manual模式=override文件存在）。
    """
    install_dir = DBACTUATOR_INSTALL_DIR_TPL.format(uid=ticket_id)
    progress_path = f"{install_dir}/{PROGRESS_FILE_NAME}"
    throttle_path = f"{install_dir}/{THROTTLE_FILE_NAME}"
    override_path = f"{install_dir}/{OVERRIDE_FILE_NAME}"
    script = f'\necho "{_STATE_DELIMITER}"\n'.join(
        [_read_file_snippet(progress_path), _read_file_snippet(throttle_path), _read_file_snippet(override_path)]
    )
    output = _run_remote_script(ip, bk_cloud_id, script, task_name=_("Kafka Rebalance: 读取进度/限速/调速模式"))
    parts = output.split(_STATE_DELIMITER)
    progress_raw = _parse_file_part(parts[0] if len(parts) > 0 else "", "progress.json")
    throttle_raw = _parse_file_part(parts[1] if len(parts) > 1 else "", "throttle_rate.txt")
    override_raw = _parse_file_part(parts[2] if len(parts) > 2 else "", "throttle_override.txt")
    return {
        "progress": progress_raw,
        "throttle_rate": throttle_raw,
        "override_mode": override_raw if override_raw in VALID_OVERRIDE_MODES else "auto",
    }


_WRITE_OK_MARKER = "__WRITE_OK__"


def set_manual_throttle_rate(
    ip: str, bk_cloud_id: int, ticket_id: int, throttle_rate: int, max_throttle_bytes_per_sec: int
) -> None:
    """
    人工设置限速：一次远程脚本原子完成两件事——写入throttle_rate.txt为指定值，并把
    throttle_override.txt标记为manual。必须合并成一次脚本执行，不能像早期实现那样先调
    write_remote_throttle_rate()再单独调一次改模式的Job：那样两次写入之间隔着两次独立的
    Job网络往返（各自秒级），中间足够sidecar插入一轮基于旧auto状态的自动调速，把刚设置的值
    覆盖掉；即使第二次Job失败，也会留下"限速已改、模式还是auto"的不一致状态，下一轮继续被
    自动逻辑改动。合并成一次脚本后，两个写入之间只隔本地mv命令的执行时间（毫秒级），
    没有网络往返可插入，且脚本要么整体成功要么set -e中途失败，不会出现"改了限速但没改
    模式"这种半成功状态残留到脚本正常退出为止。
    """
    throttle_rate = int(throttle_rate)
    if not (MIN_THROTTLE_BYTES_PER_SEC <= throttle_rate <= max_throttle_bytes_per_sec):
        raise ValueError(
            _("throttle_rate超出合法范围[{}, {}]: {}").format(
                MIN_THROTTLE_BYTES_PER_SEC, max_throttle_bytes_per_sec, throttle_rate
            )
        )

    throttle_path = f"{DBACTUATOR_INSTALL_DIR_TPL.format(uid=ticket_id)}/{THROTTLE_FILE_NAME}"
    override_path = f"{DBACTUATOR_INSTALL_DIR_TPL.format(uid=ticket_id)}/{OVERRIDE_FILE_NAME}"
    script = (
        "set -e\n"
        f'echo "{throttle_rate}" > "{throttle_path}.tmp"\n'
        f'mv "{throttle_path}.tmp" "{throttle_path}"\n'
        f'echo "manual" > "{override_path}.tmp"\n'
        f'mv "{override_path}.tmp" "{override_path}"\n'
        f'[ "$(cat "{throttle_path}")" = "{throttle_rate}" ] && [ "$(cat "{override_path}")" = "manual" ] '
        f'&& echo "{_WRITE_OK_MARKER}"'
    )
    output = _run_remote_script(ip, bk_cloud_id, script, task_name=_("Kafka Rebalance: 人工设置限速"))
    if _WRITE_OK_MARKER not in output:
        raise Exception(_("人工限速写入校验失败，远程文件内容与预期不一致"))


def clear_throttle_override(ip: str, bk_cloud_id: int, ticket_id: int) -> None:
    """
    恢复自动调速：删除throttle_override.txt，而不是把内容改写成"auto"。
    manual模式=override文件存在，auto模式=override文件不存在，语义唯一、不会有"文件存在但内容是
    auto"这种冗余状态，也不会有文件永久残留、事后无法区分"从没手动接管过"和"手动接管后又恢复了"
    的问题。不会立即触发一次调速计算，交由sidecar下一轮（最多2分钟内）按带宽利用率决定。
    """
    file_path = f"{DBACTUATOR_INSTALL_DIR_TPL.format(uid=ticket_id)}/{OVERRIDE_FILE_NAME}"
    script = f'rm -f "{file_path}" "{file_path}.tmp"\n[ ! -e "{file_path}" ] && echo "{_WRITE_OK_MARKER}"'
    output = _run_remote_script(ip, bk_cloud_id, script, task_name=_("Kafka Rebalance: 恢复自动调速"))
    if _WRITE_OK_MARKER not in output:
        raise Exception(_("恢复自动调速失败，远程override文件未能清除"))


def write_remote_throttle_rate(
    ip: str, bk_cloud_id: int, ticket_id: int, throttle_rate: int, max_throttle_bytes_per_sec: int
) -> None:
    """
    原子写入throttle_rate.txt：先写.tmp再mv，与actuator侧writeAtomically()语义保持一致，
    避免actuator轮询时读到写入中途的半截内容。
    写完立即读回校验内容一致才算成功——_run_remote_script()只看Job是否finished，
    不代表脚本本身执行成功（比如.tmp写入失败但mv被&&短路跳过，Job仍会是finished状态），
    这里加set -e+读回校验，把"Job完成"和"文件真的被正确写入"这两件事分开判断。
    调用方自身也做范围钳制，但此处仍需要再校验一次：本函数可能被sidecar之外的调用方
    （例如未来的人工调速MCP）直接复用，不能只依赖上游钳制。max_throttle_bytes_per_sec必须由
    调用方基于当前实测带宽算好传入（见get_rebalance_throttle_bounds），本函数不内置固定上限——
    不同规格集群broker带宽差异很大，写死字节数对小规格集群可能形同虚设，对大规格集群又过于保守。
    """
    throttle_rate = int(throttle_rate)
    if not (MIN_THROTTLE_BYTES_PER_SEC <= throttle_rate <= max_throttle_bytes_per_sec):
        raise ValueError(
            _("throttle_rate超出合法范围[{}, {}]: {}").format(
                MIN_THROTTLE_BYTES_PER_SEC, max_throttle_bytes_per_sec, throttle_rate
            )
        )

    file_path = f"{DBACTUATOR_INSTALL_DIR_TPL.format(uid=ticket_id)}/{THROTTLE_FILE_NAME}"
    script = (
        "set -e\n"
        f'echo "{throttle_rate}" > "{file_path}.tmp"\n'
        f'mv "{file_path}.tmp" "{file_path}"\n'
        f'[ "$(cat "{file_path}")" = "{throttle_rate}" ] && echo "{_WRITE_OK_MARKER}"'
    )
    output = _run_remote_script(ip, bk_cloud_id, script, task_name=_("Kafka Rebalance: 更新限速"))
    if _WRITE_OK_MARKER not in output:
        raise Exception(_("限速写入校验失败，远程文件内容与预期不一致"))


def resolve_and_validate_exec_ip(cluster_id: int, ip: str) -> int:
    """
    校验ip确实是该Kafka集群的broker节点，返回集群的真实bk_cloud_id（不信任调用方传入的bk_cloud_id）。
    防止sidecar/MCP工具未来被复用或传参出错时，对非本集群的任意IP执行高权限远程读写操作。
    找不到集群、集群不是Kafka类型、或ip不属于该集群broker都会抛异常，调用方应视为本轮/本次请求失败处理。
    """
    cluster = Cluster.objects.get(id=cluster_id)
    if cluster.cluster_type != ClusterType.Kafka:
        raise ValueError(_("集群{}不是Kafka集群（类型：{}）").format(cluster.immute_domain, cluster.cluster_type))
    broker_ips = set(
        cluster.storageinstance_set.filter(instance_role=InstanceRole.BROKER.value).values_list(
            "machine__ip", flat=True
        )
    )
    if ip not in broker_ips:
        raise ValueError(_("{}不是集群{}的broker节点").format(ip, cluster.immute_domain))
    return cluster.bk_cloud_id


def get_rebalance_throttle_bounds(cluster_id: int) -> Optional[Dict]:
    """
    返回本轮自动调速需要的两个信号：当前最忙broker的带宽利用率、动态限速上限。
    利用率取所有broker中的max而不是集群汇总均值——否则单个热点broker会被其他空闲broker平均掉，
    导致该broker已经打满但整体判断仍是"利用率不高"从而继续提速。
    上限=参与rebalance的broker中实测带宽最小值 * MAX_THROTTLE_BANDWIDTH_RATIO（留给客户端流量的
    余量），取min而不是max/avg——如果集群内broker规格不一致，木桶效应下瓶颈就是最慢的那台。
    带宽用监控侧script_dbm_bandwidth指标（对应/etc/dbm_bandwidth实际下发值），而不是db_meta的
    Machine.bandwidth规格字段（规格值可能是默认INT_MAX，也可能与实际配置不一致）。
    必须要求集群内所有broker的监控数据都完整才计算，只要有一台缺数据就整体返回None——
    如果只用凑得到数据的那部分broker算：漏看的broker恰好是热点（已经过载）会误判为"利用率不高"
    继续提速；漏看的broker恰好是最低带宽的那台，动态上限又会被其他broker的数据高估。
    监控数据不完整（新集群/采集延迟/部分broker缺失）时返回None，调用方应跳过本轮调速判断。
    """
    cluster = Cluster.objects.get(id=cluster_id)
    total_broker_count = cluster.storageinstance_set.filter(instance_role=InstanceRole.BROKER.value).count()
    if total_broker_count == 0:
        return None

    stats = get_broker_bandwidth_utilization(cluster_id)
    if len(stats) < total_broker_count:
        logger.warning("集群%s只有%d/%d台broker监控数据完整，跳过本轮自动调速判断", cluster_id, len(stats), total_broker_count)
        return None

    max_utilization_pct = max(s["utilization_pct"] for s in stats)
    min_bandwidth_mbps = min(s["bandwidth_mbps"] for s in stats)
    dynamic_max_bytes_per_sec = int(min_bandwidth_mbps * 1024 * 1024 / 8 * MAX_THROTTLE_BANDWIDTH_RATIO)
    return {
        "utilization_pct": max_utilization_pct,
        "max_throttle_bytes_per_sec": max(dynamic_max_bytes_per_sec, MIN_THROTTLE_BYTES_PER_SEC),
    }


def get_broker_bandwidth_utilization(cluster_id: int) -> List[Dict]:
    """
    逐台broker计算带宽利用率，返回每台broker的 [bk_target_ip, traffic_mbps, bandwidth_mbps, utilization_pct]。
    """
    cluster = Cluster.objects.get(id=cluster_id)
    brokers = list(cluster.storageinstance_set.filter(instance_role=InstanceRole.BROKER.value))
    if not brokers:
        return []
    broker_ips = {b.machine.ip for b in brokers}

    now = datetime.now()
    end_timestamp = int(timezone2timestamp(now))
    start_timestamp = int(timezone2timestamp(now - timedelta(minutes=5)))

    def _query_latest_by_ip(promql: str) -> Dict[str, float]:
        query_params = {
            "query_configs": [
                {
                    "data_source_label": "prometheus",
                    "data_type_label": "time_series",
                    "promql": promql,
                    "interval": 60,
                    "alias": "a",
                }
            ],
            "expression": "a",
            "alias": "a",
            "start_time": start_timestamp,
            "end_time": end_timestamp,
            "slimit": 500,
            "down_sample_range": "3m",
            "type": "range",
        }
        response = BKMonitorV3Api.unify_query(query_params)
        result = {}
        for series in response.get("series", []) if response else []:
            ip = series.get("dimensions", {}).get("bk_target_ip")
            values = [p[0] for p in series.get("datapoints", []) if p[0] is not None]
            if ip and values:
                result[ip] = values[-1]
        return result

    # speed_recv_bit/speed_sent_bit已经是bit/s（Kafka Dashboard验证过的指标，见
    # backend/bk_dataview/dashboards/json/kafka.json），不是bytes/s的计数器，不能再套rate()，
    # 换算Mbps时也不能再乘8——之前误当成bytes_recv/bytes_sent计数器用rate()包一层，
    # 单位和指标名都是错的
    recv_by_ip = _query_latest_by_ip(
        "max by (bk_target_ip) (avg_over_time(bkmonitor:dbm_system:net:speed_recv_bit"
        '{cluster_domain="%s",instance_role="broker"}[3m]))' % cluster.immute_domain
    )
    sent_by_ip = _query_latest_by_ip(
        "max by (bk_target_ip) (avg_over_time(bkmonitor:dbm_system:net:speed_sent_bit"
        '{cluster_domain="%s",instance_role="broker"}[3m]))' % cluster.immute_domain
    )
    # script_dbm_bandwidth 是通用带宽采集脚本指标（对应/etc/dbm_bandwidth），不带cluster_domain/instance_role
    # 维度，只能按bk_target_ip在Python侧与本集群broker IP列表关联
    bandwidth_by_ip = _query_latest_by_ip(
        "max by (bk_target_ip) (avg_over_time(bkmonitor:script_dbm_bandwidth:dbm_bandwidth[3m]))"
    )

    results = []
    for ip in broker_ips:
        # 三者必须同时有效才计算：只要有一侧监控数据缺失/延迟，就不能用另一侧当0凑出一个偏低的
        # 利用率——那样会误判为"利用率不高"从而错误提速，跟"监控数据不完整时跳过本轮调速"的
        # 原则矛盾
        if ip not in recv_by_ip or ip not in sent_by_ip or ip not in bandwidth_by_ip:
            logger.warning("broker %s 的recv/sent/bandwidth监控数据不完整，跳过该broker的利用率计算", ip)
            continue
        bandwidth_mbps = bandwidth_by_ip[ip]
        if not bandwidth_mbps:
            continue
        traffic_bits_per_sec = recv_by_ip[ip] + sent_by_ip[ip]
        traffic_mbps = traffic_bits_per_sec / 1024 / 1024
        results.append(
            {
                "bk_target_ip": ip,
                "traffic_mbps": round(traffic_mbps, 2),
                "bandwidth_mbps": bandwidth_mbps,
                "utilization_pct": round(traffic_mbps / bandwidth_mbps * 100, 2),
            }
        )
    return results
