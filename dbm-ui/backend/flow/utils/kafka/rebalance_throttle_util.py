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
from typing import Callable, Dict, List, Optional, Tuple

from django.utils.translation import gettext as _

from backend import env
from backend.components import BKMonitorV3Api, JobApi
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import AppCache, Cluster
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


def _report_skip(message: str, reporter: Optional[Callable[[str], None]] = None) -> None:
    """
    输出"本轮为什么跳过自动调速"的原因。
    调用方能传reporter时优先用调用方的日志通道：流程节点里的 self.log_info/self.log_warning 会带
    extra（root_id/node_id/version_id），JSONFormatter把这些字段一起打进日志记录，所以能按
    root_pipeline/node_id检索到。本模块的模块级logger走的是同一个flow logger，但**不带extra**，
    产出的记录里没有root_pipeline/node_id——按流程检索这些日志是搜不到的，只能当服务端日志看。
    """
    (reporter or logger.warning)(message)


def get_rebalance_throttle_bounds(cluster_id: int, on_skip: Optional[Callable[[str], None]] = None) -> Optional[Dict]:
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
    监控数据不完整（新集群/采集延迟/部分broker缺失）时返回None，调用方应跳过本轮调速判断；
    on_skip传入调用方的日志方法后，跳过的具体原因（缺哪些broker、缺的是哪类指标）会打到流程日志里。
    """
    cluster = Cluster.objects.get(id=cluster_id)
    total_broker_count = cluster.storageinstance_set.filter(instance_role=InstanceRole.BROKER.value).count()
    if total_broker_count == 0:
        _report_skip(_("集群{}在db_meta里没有broker实例，无法计算带宽利用率").format(cluster_id), on_skip)
        return None

    # 缺失明细由get_broker_bandwidth_utilization统一输出（含缺哪些IP、缺哪类指标），这里不再重复打
    stats = get_broker_bandwidth_utilization(cluster_id, on_missing=on_skip)
    if len(stats) < total_broker_count:
        _report_skip(
            _("集群{}只有{}/{}台broker带宽监控数据完整，跳过本轮自动调速判断").format(cluster_id, len(stats), total_broker_count),
            on_skip,
        )
        return None

    max_utilization_pct = max(s["utilization_pct"] for s in stats)
    min_bandwidth_mbps = min(s["bandwidth_mbps"] for s in stats)
    dynamic_max_bytes_per_sec = int(min_bandwidth_mbps * 1024 * 1024 / 8 * MAX_THROTTLE_BANDWIDTH_RATIO)
    return {
        "utilization_pct": max_utilization_pct,
        "max_throttle_bytes_per_sec": max(dynamic_max_bytes_per_sec, MIN_THROTTLE_BYTES_PER_SEC),
    }


# 每台broker带宽规格(Mbps)的表达式。利用率那条promql的分母、以及单独查带宽（动态限速上限要用到
# 绝对值取min，光靠比值拿不到）用的都是这一份，抽成常量是为了：
#   ① 窗口、聚合算子只在一处定义，改窗口时不会漏掉另一边；
#   ② 两边必须是同一个算子。原来分母写的是 avg by (bk_target_ip)、这里写的是 max by——按"每台机器
#      一条series"的现状两者等价，但一旦这个指标带上网卡/设备之类的维度，就会出现"利用率分母按平均、
#      动态上限按最大"的口径分裂：同一台机器两边算出来的带宽不是同一个值。统一取 max，跟分子
#      speed_recv_bit/speed_sent_bit 的 max by (bk_target_ip) 也一致（那两个确实是多网卡，取最忙的）。
# script_dbm_bandwidth 是通用带宽采集脚本指标（对应/etc/dbm_bandwidth），不带cluster_domain/
# instance_role维度，只能按bk_target_ip在Python侧与本集群broker IP列表关联。
# 窗口3m：这个值是装机时按机型写一次、之后不变的常量，avg_over_time的窗口宽窄不影响取值（都是
# 那个常量），宽窗口只是多一分"窗口里至少有一个样本"的容错
BANDWIDTH_PROMQL = "max by (bk_target_ip) (avg_over_time(bkmonitor:script_dbm_bandwidth:dbm_bandwidth[3m]))"


def _utilization_promql(labels: str) -> str:
    """
    利用率在监控侧一条promql里算完（拆成多次查询时，各次返回的是"自己那个时刻的最新点"，
    彼此之间有查询耗时差，用不同时刻的流量和带宽相除本身就不严谨）。
    speed_recv_bit/speed_sent_bit已经是bit/s（Kafka Dashboard验证过的指标，见
    backend/bk_dataview/dashboards/json/kafka.json），不是bytes/s的计数器，不能再套rate()，
    换算Mbit/s时也不能再乘8——之前误当成bytes_recv/bytes_sent计数器用rate()包一层，
    单位和指标名都是错的。
    单位基准：分子 /1e6 换算成Mbit/s，分母 script_dbm_bandwidth 本身就是Mbps
    （对应 DeviceClass.bandwidth 的"Mbps"，见 db_meta/models/machine.py:270），
    两者口径一致，相除即利用率。原来用 /1024/1024 得到的是Mibit/s，再除以十进制的Mbps
    会让利用率系统性偏高约4.9%（1024²/1e6），相对85%/80%两个水位不是可忽略的量。
    recv/sent/bandwidth都套3m的avg_over_time。窗口长度不是随便取的：实测这两类指标
    （bkmonitor:dbm_system:net:speed_*_bit 和 script_dbm_bandwidth:dbm_bandwidth）的
    采样周期都是60s——用 count_over_time(m[1m]) 在30分钟窗口上逐step统计，每台机器
    min=avg=max=1，也就是[1m]窗口里恰好只有一个样本。这种时候avg_over_time等于没平滑
    （平均值就是那个原始值本身），单点抖动会直接推动50MB/s的步进调整，而且余量为零——
    一旦相位漂移或漏采一个点，该step立刻变null。[3m]能装下3个样本，才是真的平滑，
    并且能容忍漏掉1~2个点。代价是最多3分钟的滞后，相对sidecar本身2分钟一轮可以忽略。
    分母直接复用 BANDWIDTH_PROMQL，保证跟"单独查带宽"那条是同一个算子、同一个窗口。
    匹配用 on(bk_target_ip)（两侧标签集不同，默认的全标签匹配会匹配不上），右侧是按IP唯一
    的聚合结果，所以是 group_left。注意 group_left 后面直接跟右操作数、不加括号——加了括号
    会被解析成 grouping label 列表而不是右操作数（仓库既有写法见
    bk_dataview/dashboards/json/hdfs.json、doris.json 的 "group_left avg by (...)"）。
    """
    sent = f"max by (bk_target_ip) (avg_over_time(bkmonitor:dbm_system:net:speed_sent_bit{{{labels}}}[3m]))"
    recv = f"max by (bk_target_ip) (avg_over_time(bkmonitor:dbm_system:net:speed_recv_bit{{{labels}}}[3m]))"
    return f"({sent} + {recv}) / 1000000 / on(bk_target_ip) group_left {BANDWIDTH_PROMQL}"


def _query_steps_by_ip(
    bk_biz_id: int, promql: str, start_timestamp: int, end_timestamp: int
) -> Tuple[int, Dict[str, Dict[float, float]]]:
    """
    返回 (原始series条数, {ip: {step时间戳: 值}})，每个ip只保留非空点。
    不在这里直接取"最后一个点"：range查询的最后一个step正好落在"现在"，这类指标有采集/计算
    延迟，末点为空是常见现象（仓库里其它取点代码也都是先filter掉null再取最后一点，见
    db_monitor/tasks.py、doris/sync_cluster_remote_used.py）。直接按末点判缺失会让整轮
    被判成数据不完整、自动调速长期不动作且不报错。真正的取点由 _pick_aligned_step 决定。
    """
    query_params = {
        "bk_biz_id": bk_biz_id,
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
    steps_by_ip: Dict[str, Dict[float, float]] = {}
    series_count = 0
    for series in response.get("series", []) if response else []:
        series_count += 1
        ip = series.get("dimensions", {}).get("bk_target_ip")
        if not ip:
            continue
        for point in series.get("datapoints", []):
            if point and point[0] is not None and len(point) > 1:
                steps_by_ip.setdefault(ip, {})[point[1]] = point[0]
    return series_count, steps_by_ip


def _pick_aligned_step(step_maps: List[Dict[str, Dict[float, float]]], broker_ips: set) -> Optional[float]:
    """
    在两条查询共有的step里，选一个"对尽可能多broker都有值"的step，覆盖数并列时取更新的那个。
    同一个step上取值，才能保证利用率跟带宽严格来自同一时刻（这是把利用率并成一条promql的
    目的）；同时又不因为末点恰好没算出来（采集延迟）就把整轮作废——那只是让取点往后挪一个
    step。覆盖率取max而不是"最新一个有数据的step"，是为了不让某一台broker的延迟把其它broker
    的数据一起拖到更陈旧的时间点上。

    返回选中的step时间戳；两条查询的step里一个可用的都没有（比如两边都没数据）时返回None，
    调用方据此把每台broker都算成"整个窗口无数据"。注意返回的step有可能只覆盖部分broker，
    甚至覆盖数为0（网格有交集、只是没有一台broker同时在两边同一个step上有值），
    "是否所有broker都被覆盖"由调用方拿结果自己判断，不在这里兜底。
    """
    candidate_steps = set()
    for ip_map in step_maps:
        for steps in ip_map.values():
            candidate_steps.update(steps)

    best_step, best_cover = None, -1
    for step in sorted(candidate_steps, reverse=True):
        cover = sum(1 for ip in broker_ips if all(step in ip_map.get(ip, {}) for ip_map in step_maps))
        if cover > best_cover:
            best_step, best_cover = step, cover
    return best_step


def _collect_broker_stats(
    broker_ips: set,
    utilization_steps: Dict[str, Dict[float, float]],
    bandwidth_steps: Dict[str, Dict[float, float]],
    aligned_step: Optional[float],
) -> Tuple[List[Dict], Dict[str, str]]:
    """
    逐台broker算利用率，返回 (结果列表, ip -> 缺失原因)。
    "整个窗口都没有"和"选了对齐step后这个step上没有"要分开：前者是采集/指标本身的问题，
    后者多半是这台机器采集延迟、落在了别的step上，排查方向完全不同。
    """
    utilization_by_ip = {ip: steps[aligned_step] for ip, steps in utilization_steps.items() if aligned_step in steps}
    bandwidth_by_ip = {ip: steps[aligned_step] for ip, steps in bandwidth_steps.items() if aligned_step in steps}

    results: List[Dict] = []
    missing: Dict[str, str] = {}
    for ip in broker_ips:
        if ip not in bandwidth_steps:
            missing[ip] = _("bandwidth指标整个窗口无数据")
            continue
        if ip not in utilization_steps:
            missing[ip] = _("recv/sent指标整个窗口无数据")
            continue
        bandwidth_mbps = bandwidth_by_ip.get(ip)
        if bandwidth_mbps is None:
            missing[ip] = _("对齐step上bandwidth无数据（采集延迟）")
            continue
        if ip not in utilization_by_ip:
            missing[ip] = _("对齐step上recv/sent无数据（采集延迟）")
            continue
        if not bandwidth_mbps:
            missing[ip] = _("bandwidth指标为0")
            continue
        utilization_pct = round(utilization_by_ip[ip] * 100, 2)
        # 流量仅作展示用，由同一个step的利用率×带宽反推，保证跟utilization_pct自洽
        traffic_mbps = round(utilization_pct / 100 * bandwidth_mbps, 2)
        results.append(
            {
                "bk_target_ip": ip,
                "traffic_mbps": traffic_mbps,
                "bandwidth_mbps": bandwidth_mbps,
                "utilization_pct": utilization_pct,
            }
        )
    return results, missing


def get_broker_bandwidth_utilization(
    cluster_id: int, on_missing: Optional[Callable[[str], None]] = None
) -> List[Dict]:
    """
    逐台broker计算带宽利用率，返回每台broker的 [bk_target_ip, traffic_mbps, bandwidth_mbps, utilization_pct]。
    on_missing是"本轮出了什么问题"的输出通道，传入调用方的日志方法（如sidecar的self.log_warning）时，
    下面这些都会打到流程日志里——不只监控数据缺失，还包括带app查询覆盖不全后退回、两条查询没有共同
    step这类情况，所以名字叫missing但语义是"本轮的异常/退化说明"：
      · 监控数据缺失的明细（缺哪些IP、缺的是哪类指标）
      · 按app查询覆盖不全、退回不带app查询的结果
      · 利用率查询与带宽查询没有共同step
    """
    cluster = Cluster.objects.get(id=cluster_id)
    brokers = list(cluster.storageinstance_set.filter(instance_role=InstanceRole.BROKER.value))
    if not brokers:
        return []
    broker_ips = {b.machine.ip for b in brokers}

    now = datetime.now()
    end_timestamp = int(timezone2timestamp(now))
    start_timestamp = int(timezone2timestamp(now - timedelta(minutes=5)))

    # app维度对应集群监控视图(Kafka Dashboard / bk_dataview/dashboards/json/kafka.json)里的 $app，
    # 取值口径跟dashboard保持一致：db_monitor/models/dashboard.py 是用
    # AppCache.get_app_attr(bk_biz_id, default=bk_biz_id) 渲染 $app 的（比直接查缓存多了CC兜底）
    app_abbr = str(AppCache.get_app_attr(cluster.bk_biz_id, default=cluster.bk_biz_id) or "")
    base_labels = f'cluster_domain="{cluster.immute_domain}",instance_role="broker"'

    utilization_series_count, utilization_steps = _query_steps_by_ip(
        cluster.bk_biz_id, _utilization_promql(f'app="{app_abbr}",{base_labels}'), start_timestamp, end_timestamp
    )
    # app的取值口径一旦跟监控series上的实际值对不上（业务改名、只有部分机器标签缺失等），
    # 加了app会让部分甚至全部broker查不到数据、功能静默失效。cluster_domain本身已能唯一定位集群，
    # 所以覆盖不全时退回不带app的查询再试一次，取覆盖更全的那次结果。这条不假设app一定有问题
    # （数据本来就全缺时这里也会触发，紧接着的缺失明细才是结论）
    if len(utilization_steps) < len(broker_ips):
        without_app_series_count, without_app_steps = _query_steps_by_ip(
            cluster.bk_biz_id, _utilization_promql(base_labels), start_timestamp, end_timestamp
        )
        if len(without_app_steps) > len(utilization_steps):
            _report_skip(
                _("集群{}按app={}查询带宽利用率只覆盖{}/{}台broker，退回不带app的查询后覆盖{}/{}台").format(
                    cluster_id,
                    app_abbr,
                    len(utilization_steps),
                    len(broker_ips),
                    len(without_app_steps),
                    len(broker_ips),
                ),
                on_missing,
            )
            utilization_series_count, utilization_steps = without_app_series_count, without_app_steps

    bandwidth_series_count, bandwidth_steps = _query_steps_by_ip(
        cluster.bk_biz_id, BANDWIDTH_PROMQL, start_timestamp, end_timestamp
    )

    # 两条查询参数相同、step网格本该一致，完全错开属于异常情况（比如两条指标来自不同的采集源/
    # 不同的时间对齐）。这时"每台broker都缺"的真正原因是没有共同step，不能落到下面的按台明细里
    # 被说成"采集延迟"（那会把人往采集侧带）。
    # 判定必须用"两个step集合无交集"，不能用"覆盖数==0"：网格有交集、只是没有任何一台broker
    # 恰好同时在两边同一个step上有数据（利用率只有A、带宽只有B）也会让覆盖数为0，那种情况
    # 按台明细（A缺bandwidth、B缺recv/sent）才是准确的
    utilization_step_set = {step for steps in utilization_steps.values() for step in steps}
    bandwidth_step_set = {step for steps in bandwidth_steps.values() for step in steps}
    if utilization_step_set and bandwidth_step_set and not (utilization_step_set & bandwidth_step_set):
        _report_skip(
            _("集群{}的利用率查询与带宽查询没有共同的step（利用率{}个step、带宽{}个step），本轮跳过自动调速").format(
                cluster_id, len(utilization_step_set), len(bandwidth_step_set)
            ),
            on_missing,
        )
        return []

    aligned_step = _pick_aligned_step([utilization_steps, bandwidth_steps], broker_ips)
    results, missing = _collect_broker_stats(broker_ips, utilization_steps, bandwidth_steps, aligned_step)

    if missing:
        _report_skip(
            _("集群{}有{}/{}台broker带宽监控数据不完整，缺失明细: {}" "（利用率查询{}条series、带宽查询{}条series，对齐step={}，app标签={}）").format(
                cluster_id,
                len(missing),
                len(broker_ips),
                dict(sorted(missing.items())),
                utilization_series_count,
                bandwidth_series_count,
                aligned_step if aligned_step is not None else _("<无可用step>"),
                app_abbr or _("<未使用>"),
            ),
            on_missing,
        )
    return results
