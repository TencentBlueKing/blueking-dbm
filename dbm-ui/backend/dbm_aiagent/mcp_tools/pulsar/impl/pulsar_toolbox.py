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
import json
import logging
import shlex
import time
from typing import Dict, List

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend import env
from backend.components import DBConfigApi, JobApi
from backend.components.dbconfig.constants import FormatType, LevelName, ReqType
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.common.impl.job import get_job_exec_status
from backend.flow.consts import DBA_ROOT_USER, ConfigTypeEnum, NameSpaceEnum, PulsarRoleEnum
from backend.flow.utils.pulsar.consts import PULSAR_BROKER_METRICS_PORT
from backend.utils.string import base64_encode

logger = logging.getLogger("root")

# Pulsar 安装路径常量，与 dbactuator 的 cst/pulsar.go 保持一致
PULSAR_ENV_DIR = "/data/pulsarenv"
PULSAR_BROKER_DIR = f"{PULSAR_ENV_DIR}/broker"
PULSAR_ADMIN = f"{PULSAR_BROKER_DIR}/bin/pulsar-admin"
PULSAR_JAVA_HOME = f"{PULSAR_ENV_DIR}/java/jdk"

# 轮询 Job 状态的参数
JOB_POLL_INTERVAL = 5  # 秒
JOB_POLL_MAX_RETRIES = 60  # 最多轮询 60 次，即 5 分钟

# 健康检查各段输出的分隔符
HEALTH_SECTION_MARKERS = {
    "===HEALTHCHECK===": "healthcheck",
    "===BROKERS===": "brokers",
}


def get_broker_web_service_port(bk_biz_id: int, major_version: str) -> int:
    """
    从 dbconfig 获取 broker 的 webServicePort（pulsar-admin 的 HTTP 管理端口）。
    取不到时回退到默认端口，逻辑与 flow/utils/pulsar/pulsar_module_operate.py 保持一致。
    """
    try:
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(bk_biz_id),
                "level_name": LevelName.APP,
                "level_value": str(bk_biz_id),
                "conf_file": major_version,
                "conf_type": ConfigTypeEnum.DBConf,
                "namespace": NameSpaceEnum.Pulsar,
                "format": FormatType.MAP_LEVEL,
                "method": ReqType.GENERATE_AND_PUBLISH,
            }
        )
        port = data["content"][PulsarRoleEnum.Broker].get("webServicePort", PULSAR_BROKER_METRICS_PORT)
        return int(port)
    except Exception as e:  # noqa
        logger.warning("获取 Pulsar broker webServicePort 失败，回退默认端口 %s: %s", PULSAR_BROKER_METRICS_PORT, e)
        return PULSAR_BROKER_METRICS_PORT


def resolve_cluster_connection_info(immute_domain: str) -> Dict:
    """
    解析集群连接信息，挑一个 broker 节点作为 pulsar-admin 的执行机器。

    Returns:
        {
            "cluster_id": int,
            "bk_biz_id": int,
            "cluster_name": str,
            "broker_ip": str,
            "broker_port": int,
            "admin_url": str,
            "bk_host_id": int,
            "bk_cloud_id": int,
            "major_version": str,
        }
    """
    try:
        cluster = Cluster.objects.get(immute_domain=immute_domain)
    except Cluster.DoesNotExist:
        raise serializers.ValidationError(_("集群不存在: {}").format(immute_domain))
    # immute_domain 全局唯一，理论上不会查到非 Pulsar 集群，这里显式校验避免对非
    # Pulsar 集群按 PULSAR_BROKER 角色过滤时只能报出"没有可用 broker 节点"这种不够
    # 直接的错误，而是明确指出集群类型不对
    if cluster.cluster_type != ClusterType.Pulsar.value:
        raise serializers.ValidationError(
            _("集群 {} 不是 Pulsar 类型集群（实际类型: {}）").format(immute_domain, cluster.cluster_type)
        )

    # pulsar-admin 依赖 broker 节点上的 client.conf（安装时已写入 token），只能在 broker 上执行
    broker = cluster.storageinstance_set.filter(instance_role=InstanceRole.PULSAR_BROKER.value).first()
    if not broker:
        raise serializers.ValidationError(_("集群 {} 没有可用的 broker 节点").format(immute_domain))

    # broker 的 web 服务不监听 localhost，pulsar-admin 默认的 localhost:8080 连不上，
    # 必须显式用本机 IP 拼出 --admin-url
    web_port = get_broker_web_service_port(cluster.bk_biz_id, cluster.major_version)

    return {
        "cluster_id": cluster.id,
        "bk_biz_id": cluster.bk_biz_id,
        "cluster_name": cluster.name,
        "broker_ip": broker.machine.ip,
        "broker_port": broker.port,
        "admin_url": f"http://{broker.machine.ip}:{web_port}",
        "bk_host_id": broker.machine.bk_host_id,
        "bk_cloud_id": cluster.bk_cloud_id,
        "major_version": cluster.major_version,
    }


def build_pulsar_cli_script(connection_info: Dict, admin_args: str) -> str:
    """
    构建在 broker 节点上执行 pulsar-admin 的 shell 脚本。

    两点与 Kafka 不同：
    1. 不需要显式传认证参数 —— 安装 broker 时已把 token 写入 broker/conf/client.conf 的 authParams
    2. 必须显式指定 --admin-url —— broker 的 web 服务不监听 localhost，
       用默认值会报 "Connection refused" 错误

    Args:
        connection_info: resolve_cluster_connection_info 返回的集群信息
        admin_args: pulsar-admin 的子命令与参数，如 "tenants list"

    Returns:
        完整的 shell 脚本内容
    """
    # 过滤 JVM/日志框架噪音，|| true 兜底避免全部被过滤后管道退出码非 0
    return f"""#!/bin/bash

export JAVA_HOME={PULSAR_JAVA_HOME}
export PATH=$JAVA_HOME/bin:$PATH

{PULSAR_ADMIN} --admin-url {connection_info["admin_url"]} {admin_args} 2>&1 | \
{{ grep -v "^SLF4J" | grep -v "^WARN" | grep -v "^Picked up" || true; }}
"""


def _run_job_and_wait(connection_info: Dict, script: str, task_name: str, timeout: int = 300) -> str:
    """提交脚本到作业平台并轮询结果，返回合并后的日志内容"""
    target_ips = [{"ip": connection_info["broker_ip"], "bk_cloud_id": connection_info["bk_cloud_id"]}]

    body = {
        "account_alias": DBA_ROOT_USER,
        "bk_scope_type": "biz_set",
        "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
        "task_name": task_name,
        "script_content": base64_encode(script),
        "script_language": 1,
        "target_server": {"ip_list": target_ips},
        "timeout": timeout,
    }
    job_task = JobApi.fast_execute_script(body, use_admin=True)

    # 轮询 Job 状态直到完成（先检查再 sleep，避免不必要的等待）
    job_instance_id = job_task["job_instance_id"]
    for _i in range(JOB_POLL_MAX_RETRIES):
        job_resp = get_job_exec_status(job_instance_id)
        if job_resp["finished"]:
            log_content_parts = []
            for log_entry in job_resp["job_log_resp"]:
                if log_entry.get("log_content"):
                    log_content_parts.append(log_entry["log_content"])
            return "\n".join(log_content_parts)
        time.sleep(JOB_POLL_INTERVAL)

    raise Exception(_("执行 pulsar-admin 命令超时: {}").format(task_name))


def execute_pulsar_cli(
    immute_domain: str,
    admin_args: str,
    task_name: str = "pulsar admin cli",
    timeout: int = 300,
) -> str:
    """
    在目标 broker 上远程执行 pulsar-admin 命令。

    Args:
        immute_domain: 集群域名
        admin_args: pulsar-admin 子命令与参数
        task_name: Job 任务名称
        timeout: 超时秒数

    Returns:
        CLI 输出的文本内容
    """
    connection_info = resolve_cluster_connection_info(immute_domain)
    script = build_pulsar_cli_script(connection_info, admin_args)
    return _run_job_and_wait(connection_info, script, task_name, timeout)


# ============================================================
# 输出解析
# ============================================================


def parse_line_list(output: str) -> List[str]:
    """
    解析逐行输出的 list 类命令（tenants/namespaces/topics/brokers list）。

    Pulsar 的实体名都不含空白字符（如 public、public/default、
    persistent://tenant/ns/topic、host:port 形式的 broker 地址），而日志行和异常堆栈必然含空格，
    因此以「是否含空白」作为过滤依据。

    额外剔除 "null" —— pulsar-admin 调用失败时会输出 "null" 加一段 Reason 堆栈，
    若不过滤会被误判成一个有效条目。
    """
    return [
        line.strip()
        for line in output.splitlines()
        if line.strip() and line.strip() != "null" and not any(c.isspace() for c in line.strip())
    ]


def parse_json_output(output: str, task_desc: str) -> Dict:
    """
    解析返回 JSON 的命令（topics stats / namespaces policies 等）。
    作业平台日志可能带前导杂行，从第一个 '{' 开始截取。
    """
    start = output.find("{")
    if start < 0:
        raise Exception(_("{} 未返回预期的 JSON 输出: {}").format(task_desc, output[:500]))
    try:
        return json.loads(output[start:])
    except json.JSONDecodeError as e:
        raise Exception(_("{} 输出解析失败: {}").format(task_desc, e))


# ============================================================
# 工具函数：只读操作
# ============================================================


def list_tenants(immute_domain: str) -> Dict:
    """列出集群所有租户"""
    output = execute_pulsar_cli(
        immute_domain=immute_domain,
        admin_args="tenants list",
        task_name=_("Pulsar: 列出所有租户"),
    )
    tenants = parse_line_list(output)
    return {"tenants": tenants, "count": len(tenants)}


def list_namespaces(immute_domain: str, tenant: str) -> Dict:
    """列出指定租户下的所有 namespace"""
    output = execute_pulsar_cli(
        immute_domain=immute_domain,
        admin_args=f"namespaces list {shlex.quote(tenant)}",
        task_name=_("Pulsar: 列出租户下的namespace"),
    )
    namespaces = parse_line_list(output)
    return {"tenant": tenant, "namespaces": namespaces, "count": len(namespaces)}


def list_topics(immute_domain: str, namespace: str) -> Dict:
    """列出指定 namespace 下的所有 topic"""
    output = execute_pulsar_cli(
        immute_domain=immute_domain,
        admin_args=f"topics list {shlex.quote(namespace)}",
        task_name=_("Pulsar: 列出namespace下的topic"),
    )
    topics = parse_line_list(output)
    return {"namespace": namespace, "topics": topics, "count": len(topics)}


def describe_topic(immute_domain: str, topic: str) -> Dict:
    """
    查看 topic 统计信息，包含生产/消费速率、存储大小、各订阅的积压等。
    topic 需为完整名称，如 persistent://tenant/namespace/topic
    """
    output = execute_pulsar_cli(
        immute_domain=immute_domain,
        admin_args=f"topics stats {shlex.quote(topic)}",
        task_name=_("Pulsar: 查看topic统计"),
    )
    stats = parse_json_output(output, _("查看topic统计"))
    return {"topic": topic, "stats": stats}


def topic_internal_stats(immute_domain: str, topic: str) -> Dict:
    """查看 topic 内部存储状态（ledger 分布、entry 数量等），用于排查存储层问题"""
    output = execute_pulsar_cli(
        immute_domain=immute_domain,
        admin_args=f"topics stats-internal {shlex.quote(topic)}",
        task_name=_("Pulsar: 查看topic内部状态"),
    )
    stats = parse_json_output(output, _("查看topic内部状态"))
    return {"topic": topic, "internal_stats": stats}


def list_subscriptions(immute_domain: str, topic: str) -> Dict:
    """列出 topic 的所有订阅"""
    output = execute_pulsar_cli(
        immute_domain=immute_domain,
        admin_args=f"topics subscriptions {shlex.quote(topic)}",
        task_name=_("Pulsar: 列出topic订阅"),
    )
    subscriptions = parse_line_list(output)
    return {"topic": topic, "subscriptions": subscriptions, "count": len(subscriptions)}


def get_namespace_policies(immute_domain: str, namespace: str) -> Dict:
    """查看 namespace 策略配置，含 retention、持久化策略、限流等"""
    output = execute_pulsar_cli(
        immute_domain=immute_domain,
        admin_args=f"namespaces policies {shlex.quote(namespace)}",
        task_name=_("Pulsar: 查看namespace策略"),
    )
    policies = parse_json_output(output, _("查看namespace策略"))
    return {"namespace": namespace, "policies": policies}


def list_brokers(immute_domain: str) -> Dict:
    """列出集群所有在线 broker"""
    connection_info = resolve_cluster_connection_info(immute_domain)
    cluster_name = connection_info["cluster_name"]
    script = build_pulsar_cli_script(connection_info, f"brokers list {shlex.quote(cluster_name)}")
    output = _run_job_and_wait(connection_info, script, _("Pulsar: 列出在线broker"))
    brokers = parse_line_list(output)
    return {"cluster_name": cluster_name, "brokers": brokers, "count": len(brokers)}


def cluster_health_check(immute_domain: str) -> Dict:
    """
    集群健康检查（合并为一次 Job 调用，避免多次串行调用的延迟）：
    1. brokers healthcheck — broker 自检
    2. brokers list — 列出在线 broker

    说明：BookKeeper 的 under-replicated ledger 检查需在 bookie 节点执行
    （二进制在 /data/pulsarenv/bookkeeper/bin/bookkeeper），本工具只覆盖 broker 侧。
    """
    connection_info = resolve_cluster_connection_info(immute_domain)
    cluster_name = connection_info["cluster_name"]
    admin_url = connection_info["admin_url"]

    script = f"""#!/bin/bash

export JAVA_HOME={PULSAR_JAVA_HOME}
export PATH=$JAVA_HOME/bin:$PATH

# broker 的 web 服务不监听 localhost，必须显式指定 --admin-url
PADMIN="{PULSAR_ADMIN} --admin-url {admin_url}"
FILTER='grep -v "^SLF4J" | grep -v "^WARN" | grep -v "^Picked up"'

echo "===HEALTHCHECK==="
$PADMIN brokers healthcheck 2>&1 | eval $FILTER || true

echo "===BROKERS==="
$PADMIN brokers list {shlex.quote(cluster_name)} 2>&1 | eval $FILTER || true
"""

    raw_output = _run_job_and_wait(connection_info, script, _("Pulsar: 集群健康检查"))

    # 按分隔符拆分各段输出
    sections = {"healthcheck": "", "brokers": ""}
    current_section = ""
    for line in raw_output.splitlines():
        marker = HEALTH_SECTION_MARKERS.get(line.strip())
        if marker:
            current_section = marker
        elif current_section:
            sections[current_section] += line + "\n"

    brokers = parse_line_list(sections["brokers"])
    # healthcheck 正常时返回 "ok"
    healthcheck_output = sections["healthcheck"].strip()
    healthcheck_ok = "ok" in healthcheck_output.lower()

    return {
        "cluster_name": cluster_name,
        "healthcheck_ok": healthcheck_ok,
        "healthcheck_output": healthcheck_output,
        "brokers": brokers,
        "broker_count": len(brokers),
        "healthy": healthcheck_ok and len(brokers) > 0,
    }
