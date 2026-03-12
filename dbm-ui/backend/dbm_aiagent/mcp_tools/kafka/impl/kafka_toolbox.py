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
from typing import Dict, List

from django.utils.translation import gettext_lazy as _

from backend import env
from backend.components import JobApi
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.common.impl.job import get_job_exec_status
from backend.flow.consts import DBA_ROOT_USER
from backend.utils.string import base64_encode

logger = logging.getLogger("root")

# Kafka 安装路径常量
KAFKA_ENV_DIR = "/data/kafkaenv"
KAFKA_BIN_DIR = f"{KAFKA_ENV_DIR}/kafka/bin"
KAFKA_CONFIG_DIR = f"{KAFKA_ENV_DIR}/kafka/config"
KAFKA_JAVA_HOME = f"{KAFKA_ENV_DIR}/jdk"
KAFKA_SERVER_PROPERTIES = f"{KAFKA_CONFIG_DIR}/server.properties"
KAFKA_SCRAM_JAAS_CONF = f"{KAFKA_CONFIG_DIR}/kafka_server_scram_jaas.conf"
KAFKA_CLIENT_PROPERTIES = f"{KAFKA_ENV_DIR}/kafka/client.properties"

# 轮询 Job 状态的参数
JOB_POLL_INTERVAL = 5  # 秒
JOB_POLL_MAX_RETRIES = 60  # 最多轮询 60 次，即 5 分钟


def resolve_cluster_connection_info(immute_domain: str) -> Dict:
    """
    解析集群连接信息，获取 broker 节点和 zookeeper 信息。

    Returns:
        {
            "cluster_id": int,
            "bk_biz_id": int,
            "broker_ip": str,
            "broker_port": int,
            "bk_host_id": int,
            "bk_cloud_id": int,
            "major_version": str,
            "zookeeper_ips": list[str],
        }
    """
    cluster = Cluster.objects.get(immute_domain=immute_domain)

    # 获取第一个可用 broker
    broker = cluster.storageinstance_set.filter(instance_role=InstanceRole.BROKER.value).first()
    if not broker:
        raise Exception(_("集群 {} 没有可用的 broker 节点").format(immute_domain))

    # 获取 zookeeper IP 列表
    zk_instances = cluster.storageinstance_set.filter(instance_role=InstanceRole.ZOOKEEPER.value)
    zookeeper_ips = [zk.machine.ip for zk in zk_instances]

    return {
        "cluster_id": cluster.id,
        "bk_biz_id": cluster.bk_biz_id,
        "broker_ip": broker.machine.ip,
        "broker_port": broker.port,
        "bk_host_id": broker.machine.bk_host_id,
        "bk_cloud_id": cluster.bk_cloud_id,
        "major_version": cluster.major_version,
        "zookeeper_ips": zookeeper_ips,
    }


def build_kafka_cli_script(connection_info: Dict, kafka_bin: str, cli_args: str) -> str:
    """
    构建在目标 broker 上执行的 shell 脚本。

    运行时自动检测：
    - 连接方式：版本 0.x 且 CLI 支持 --zookeeper 则用 ZK 连接，否则用 --bootstrap-server
    - SCRAM 认证：检测 JAAS 文件是否存在，存在则追加 --command-config

    Args:
        connection_info: resolve_cluster_connection_info 返回的集群信息
        kafka_bin: kafka CLI 工具名称，如 kafka-topics.sh
        cli_args: CLI 参数字符串

    Returns:
        完整的 shell 脚本内容
    """
    broker_ip = connection_info["broker_ip"]
    broker_port = connection_info["broker_port"]

    script = f"""#!/bin/bash
set -e

export JAVA_HOME={KAFKA_JAVA_HOME}
export PATH=$JAVA_HOME/bin:$PATH

KAFKA_BIN="{KAFKA_BIN_DIR}/{kafka_bin}"
BOOTSTRAP_SERVER="{broker_ip}:{broker_port}"
USE_ZK=0

# 运行时检测连接模式（help 内容在 stderr，需要 2>&1 捕获，用 grep -F 精确匹配避免转义问题）
CONNECTION_ARG=""
if $KAFKA_BIN --help 2>&1 | grep -qF -- '--zookeeper'; then
    # 支持 --zookeeper，从 server.properties 读取 zookeeper.connect
    ZK_CONNECT=$(grep '^zookeeper.connect=' {KAFKA_SERVER_PROPERTIES} 2>/dev/null | head -1 | cut -d'=' -f2-)
    if [ -n "$ZK_CONNECT" ]; then
        CONNECTION_ARG="--zookeeper $ZK_CONNECT"
        USE_ZK=1
    else
        CONNECTION_ARG="--bootstrap-server $BOOTSTRAP_SERVER"
    fi
else
    CONNECTION_ARG="--bootstrap-server $BOOTSTRAP_SERVER"
fi

# SCRAM 认证仅在 bootstrap-server 模式下需要，zookeeper 模式不需要
AUTH_ARG=""
if [ "$USE_ZK" -eq 0 ] && [ -f "{KAFKA_SCRAM_JAAS_CONF}" ]; then
    AUTH_ARG="--command-config {KAFKA_CLIENT_PROPERTIES}"
fi

# 执行 kafka CLI 命令（过滤已知噪音，保留真实错误信息）
$KAFKA_BIN $CONNECTION_ARG {cli_args} $AUTH_ARG 2>&1 | grep -v "^SLF4J" | grep -v "^egrep:" | grep -v "stray"
"""
    return script


def execute_kafka_cli(
    immute_domain: str,
    kafka_bin: str,
    cli_args: str,
    task_name: str = "kafka cli",
    timeout: int = 300,
) -> str:
    """
    在目标 broker 上远程执行 kafka CLI 命令。

    Args:
        immute_domain: 集群域名
        kafka_bin: kafka CLI 工具名称
        cli_args: CLI 参数
        task_name: Job 任务名称
        timeout: 超时秒数

    Returns:
        CLI 输出的文本内容
    """
    connection_info = resolve_cluster_connection_info(immute_domain)
    script = build_kafka_cli_script(connection_info, kafka_bin, cli_args)

    target_ips = [{"ip": connection_info["broker_ip"], "bk_cloud_id": connection_info["bk_cloud_id"]}]

    body = {
        "account_alias": DBA_ROOT_USER,
        "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
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
            # 提取日志输出
            log_content_parts = []
            for log_entry in job_resp["job_log_resp"]:
                if log_entry.get("log_content"):
                    log_content_parts.append(log_entry["log_content"])
            return "\n".join(log_content_parts)
        time.sleep(JOB_POLL_INTERVAL)

    raise Exception(_("执行 Kafka CLI 命令超时: {}").format(task_name))


# ============================================================
# 工具函数：只读操作
# ============================================================


def list_topics(immute_domain: str) -> Dict:
    """列出集群所有 topic"""
    output = execute_kafka_cli(
        immute_domain=immute_domain,
        kafka_bin="kafka-topics.sh",
        cli_args="--list",
        task_name=_("Kafka: 列出所有 topic"),
    )
    return parse_list_topics(output)


def describe_topic(immute_domain: str, topic: str) -> Dict:
    """查看 topic 详细信息"""
    output = execute_kafka_cli(
        immute_domain=immute_domain,
        kafka_bin="kafka-topics.sh",
        cli_args=f"--describe --topic {topic}",
        task_name=_("Kafka: 查看 topic 详情"),
    )
    return parse_describe_topic(output)


def list_consumer_groups(immute_domain: str) -> Dict:
    """列出所有消费组"""
    output = execute_kafka_cli(
        immute_domain=immute_domain,
        kafka_bin="kafka-consumer-groups.sh",
        cli_args="--list",
        task_name=_("Kafka: 列出所有消费组"),
    )
    return parse_list_consumer_groups(output)


def describe_consumer_group(immute_domain: str, group: str) -> Dict:
    """查看消费组详细信息"""
    output = execute_kafka_cli(
        immute_domain=immute_domain,
        kafka_bin="kafka-consumer-groups.sh",
        cli_args=f"--describe --group {group}",
        task_name=_("Kafka: 查看消费组详情"),
    )
    return parse_describe_consumer_group(output)


def get_topic_config(immute_domain: str, topic: str) -> Dict:
    """查看 topic 配置"""
    output = execute_kafka_cli(
        immute_domain=immute_domain,
        kafka_bin="kafka-configs.sh",
        cli_args=f"--describe --entity-type topics --entity-name {topic}",
        task_name=_("Kafka: 查看 topic 配置"),
    )
    return parse_config_output(output, "topic", topic)


def get_broker_config(immute_domain: str, broker_id: int) -> Dict:
    """查看 broker 配置"""
    output = execute_kafka_cli(
        immute_domain=immute_domain,
        kafka_bin="kafka-configs.sh",
        cli_args=f"--describe --entity-type brokers --entity-name {broker_id}",
        task_name=_("Kafka: 查看 broker 配置"),
    )
    return parse_config_output(output, "broker", str(broker_id))


def cluster_health_check(immute_domain: str) -> Dict:
    """
    集群健康检查（合并为一次 Job 调用，避免 3 次串行调用的 15s+ 延迟）：
    1. kafka-broker-api-versions.sh — 列出所有在线 broker
    2. kafka-topics.sh --describe --under-replicated-partitions — 副本不足的分区
    3. kafka-topics.sh --describe --unavailable-partitions — 不可用的分区
    """
    connection_info = resolve_cluster_connection_info(immute_domain)
    broker_ip = connection_info["broker_ip"]
    broker_port = connection_info["broker_port"]

    script = f"""#!/bin/bash
set -e

export JAVA_HOME={KAFKA_JAVA_HOME}
export PATH=$JAVA_HOME/bin:$PATH

BOOTSTRAP_SERVER="{broker_ip}:{broker_port}"
USE_ZK=0

# 运行时检测连接模式
CONNECTION_ARG=""
if {KAFKA_BIN_DIR}/kafka-topics.sh --help 2>&1 | grep -qF -- '--zookeeper'; then
    ZK_CONNECT=$(grep '^zookeeper.connect=' {KAFKA_SERVER_PROPERTIES} 2>/dev/null | head -1 | cut -d'=' -f2-)
    if [ -n "$ZK_CONNECT" ]; then
        CONNECTION_ARG="--zookeeper $ZK_CONNECT"
        USE_ZK=1
    else
        CONNECTION_ARG="--bootstrap-server $BOOTSTRAP_SERVER"
    fi
else
    CONNECTION_ARG="--bootstrap-server $BOOTSTRAP_SERVER"
fi

AUTH_ARG=""
if [ "$USE_ZK" -eq 0 ] && [ -f "{KAFKA_SCRAM_JAAS_CONF}" ]; then
    AUTH_ARG="--command-config {KAFKA_CLIENT_PROPERTIES}"
fi

echo "===BROKERS==="
{KAFKA_BIN_DIR}/kafka-broker-api-versions.sh --bootstrap-server $BOOTSTRAP_SERVER $AUTH_ARG 2>/dev/null || true

echo "===UNDER_REPLICATED==="
{KAFKA_BIN_DIR}/kafka-topics.sh $CONNECTION_ARG --describe --under-replicated-partitions $AUTH_ARG 2>/dev/null || true

echo "===UNAVAILABLE==="
{KAFKA_BIN_DIR}/kafka-topics.sh $CONNECTION_ARG --describe --unavailable-partitions $AUTH_ARG 2>/dev/null || true
"""

    target_ips = [{"ip": connection_info["broker_ip"], "bk_cloud_id": connection_info["bk_cloud_id"]}]

    body = {
        "account_alias": DBA_ROOT_USER,
        "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
        "task_name": _("Kafka: 集群健康检查"),
        "script_content": base64_encode(script),
        "script_language": 1,
        "target_server": {"ip_list": target_ips},
        "timeout": 300,
    }
    job_task = JobApi.fast_execute_script(body, use_admin=True)

    job_instance_id = job_task["job_instance_id"]
    for _i in range(JOB_POLL_MAX_RETRIES):
        job_resp = get_job_exec_status(job_instance_id)
        if job_resp["finished"]:
            log_content_parts = []
            for log_entry in job_resp["job_log_resp"]:
                if log_entry.get("log_content"):
                    log_content_parts.append(log_entry["log_content"])
            raw_output = "\n".join(log_content_parts)

            # 按分隔符拆分三段输出
            sections = {"brokers": "", "under_replicated": "", "unavailable": ""}
            current_section = ""
            for line in raw_output.splitlines():
                if line.strip() == "===BROKERS===":
                    current_section = "brokers"
                elif line.strip() == "===UNDER_REPLICATED===":
                    current_section = "under_replicated"
                elif line.strip() == "===UNAVAILABLE===":
                    current_section = "unavailable"
                elif current_section:
                    sections[current_section] += line + "\n"

            brokers = parse_broker_api_versions(sections["brokers"])
            under_replicated = parse_under_replicated_partitions(sections["under_replicated"])
            unavailable = parse_unavailable_partitions(sections["unavailable"])

            return {
                "brokers": brokers,
                "broker_count": len(brokers),
                "under_replicated_partitions": under_replicated,
                "under_replicated_count": len(under_replicated),
                "unavailable_partitions": unavailable,
                "unavailable_count": len(unavailable),
                "healthy": len(under_replicated) == 0 and len(unavailable) == 0,
            }
        time.sleep(JOB_POLL_INTERVAL)

    raise Exception(_("集群健康检查超时"))


def consume_topic_sample(
    immute_domain: str, topic: str, max_messages: int = 10, from_beginning: bool = True, timeout_ms: int = 10000
) -> Dict:
    """采样 topic 消息"""
    connection_info = resolve_cluster_connection_info(immute_domain)
    broker_ip = connection_info["broker_ip"]
    broker_port = connection_info["broker_port"]

    # kafka-console-consumer.sh 的认证参数是 --consumer.config 而不是 --command-config
    script = f"""#!/bin/bash
set -e

export JAVA_HOME={KAFKA_JAVA_HOME}
export PATH=$JAVA_HOME/bin:$PATH

KAFKA_BIN="{KAFKA_BIN_DIR}/kafka-console-consumer.sh"
BOOTSTRAP_SERVER="{broker_ip}:{broker_port}"

# SCRAM 认证
AUTH_ARG=""
if [ -f "{KAFKA_SCRAM_JAAS_CONF}" ]; then
    AUTH_ARG="--consumer.config {KAFKA_CLIENT_PROPERTIES}"
fi

$KAFKA_BIN --bootstrap-server $BOOTSTRAP_SERVER --topic {topic} \
    --max-messages {max_messages} --timeout-ms {timeout_ms} \
    {"--from-beginning" if from_beginning else ""} \
    $AUTH_ARG 2>/dev/null
"""

    target_ips = [{"ip": connection_info["broker_ip"], "bk_cloud_id": connection_info["bk_cloud_id"]}]

    body = {
        "account_alias": DBA_ROOT_USER,
        "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
        "task_name": _("Kafka: 采样 topic 消息"),
        "script_content": base64_encode(script),
        "script_language": 1,
        "target_server": {"ip_list": target_ips},
        "timeout": 60,
    }
    job_task = JobApi.fast_execute_script(body, use_admin=True)

    job_instance_id = job_task["job_instance_id"]
    for _i in range(JOB_POLL_MAX_RETRIES):
        job_resp = get_job_exec_status(job_instance_id)
        if job_resp["finished"]:
            log_content_parts = []
            for log_entry in job_resp["job_log_resp"]:
                if log_entry.get("log_content"):
                    log_content_parts.append(log_entry["log_content"])
            raw_output = "\n".join(log_content_parts)
            messages = [line for line in raw_output.strip().splitlines() if line.strip()]
            return {"topic": topic, "messages": messages, "count": len(messages)}
        time.sleep(JOB_POLL_INTERVAL)

    raise Exception(_("采样 topic 消息超时"))


# ============================================================
# 工具函数：写操作
# ============================================================


def alter_topic_config(immute_domain: str, topic: str, config_key: str, config_value: str) -> Dict:
    """修改 topic 配置"""
    output = execute_kafka_cli(
        immute_domain=immute_domain,
        kafka_bin="kafka-configs.sh",
        cli_args=f"--alter --entity-type topics --entity-name {topic} --add-config {config_key}={config_value}",
        task_name=_("Kafka: 修改 topic 配置"),
    )
    return {"success": True, "topic": topic, "config_key": config_key, "config_value": config_value, "output": output}


def alter_topic_partitions(immute_domain: str, topic: str, partitions: int) -> Dict:
    """修改 topic 分区数（只能增加不能减少）"""
    output = execute_kafka_cli(
        immute_domain=immute_domain,
        kafka_bin="kafka-topics.sh",
        cli_args=f"--alter --topic {topic} --partitions {partitions}",
        task_name=_("Kafka: 修改 topic 分区数"),
    )
    return {"success": True, "topic": topic, "partitions": partitions, "output": output}


def delete_topic_config(immute_domain: str, topic: str, config_key: str) -> Dict:
    """删除 topic 配置（重置为默认值）"""
    output = execute_kafka_cli(
        immute_domain=immute_domain,
        kafka_bin="kafka-configs.sh",
        cli_args=f"--alter --entity-type topics --entity-name {topic} --delete-config {config_key}",
        task_name=_("Kafka: 重置 topic 配置"),
    )
    return {"success": True, "topic": topic, "config_key": config_key, "output": output}


def reset_consumer_group_offset(
    immute_domain: str, group: str, topic: str, strategy: str, strategy_value: str = ""
) -> Dict:
    """
    重置消费组 offset。

    strategy 支持：
    - to-earliest: 重置到最早
    - to-latest: 重置到最新
    - to-offset: 重置到指定 offset（strategy_value 为 offset 数值）
    - to-datetime: 重置到指定时间点（strategy_value 为 'YYYY-MM-DDTHH:mm:ss.000' 格式）
    """
    strategy_arg_map = {
        "to-earliest": "--to-earliest",
        "to-latest": "--to-latest",
        "to-offset": f"--to-offset {strategy_value}",
        "to-datetime": f"--to-datetime {strategy_value}",
    }

    strategy_arg = strategy_arg_map.get(strategy)
    if not strategy_arg:
        raise Exception(_("不支持的 offset 重置策略: {}").format(strategy))

    output = execute_kafka_cli(
        immute_domain=immute_domain,
        kafka_bin="kafka-consumer-groups.sh",
        cli_args=f"--group {group} --topic {topic} --reset-offsets {strategy_arg} --execute",
        task_name=_("Kafka: 重置消费组 offset"),
    )
    return {"success": True, "group": group, "topic": topic, "strategy": strategy, "output": output}


# ============================================================
# 输出解析函数
# ============================================================


def parse_list_topics(output: str) -> Dict:
    """解析 kafka-topics.sh --list 的输出"""
    lines = [line.strip() for line in output.strip().splitlines() if line.strip()]
    return {"topics": lines, "count": len(lines)}


def parse_describe_topic(output: str) -> Dict:
    """解析 kafka-topics.sh --describe 的输出"""
    lines = output.strip().splitlines()
    result = {"topic": "", "partition_count": 0, "replication_factor": 0, "configs": {}, "partitions": []}

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Topic 概览行: Topic: test  TopicId: xxx  PartitionCount: 3  ReplicationFactor: 2  Configs: ...
        if line.startswith("Topic:") and "PartitionCount:" in line:
            _parse_topic_summary_line(line, result)

        # 分区行: Topic: test  Partition: 0  Leader: 1  Replicas: 1,2  Isr: 1,2
        elif line.startswith("Topic:") and "Partition:" in line:
            partition_info = _parse_topic_partition_line(line)
            if partition_info:
                result["partitions"].append(partition_info)

    return result


def _parse_topic_summary_line(line: str, result: Dict):
    """解析 topic 概览行"""
    parts = line.split("\t")
    for part in parts:
        part = part.strip()
        if part.startswith("Topic:"):
            result["topic"] = part.split(":", 1)[1].strip()
        elif part.startswith("PartitionCount:"):
            try:
                result["partition_count"] = int(part.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif part.startswith("ReplicationFactor:"):
            try:
                result["replication_factor"] = int(part.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif part.startswith("Configs:"):
            config_str = part.split(":", 1)[1].strip()
            if config_str:
                for kv in config_str.split(","):
                    kv = kv.strip()
                    if "=" in kv:
                        k, v = kv.split("=", 1)
                        result["configs"][k.strip()] = v.strip()


def _parse_topic_partition_line(line: str) -> Dict:
    """解析 topic 分区行"""
    partition_info = {}
    parts = line.split("\t")
    for part in parts:
        part = part.strip()
        if part.startswith("Partition:"):
            try:
                partition_info["partition"] = int(part.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif part.startswith("Leader:"):
            try:
                partition_info["leader"] = int(part.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif part.startswith("Replicas:"):
            replica_str = part.split(":", 1)[1].strip()
            partition_info["replicas"] = [int(r) for r in replica_str.split(",") if r.strip().isdigit()]
        elif part.startswith("Isr:"):
            isr_str = part.split(":", 1)[1].strip()
            partition_info["isr"] = [int(r) for r in isr_str.split(",") if r.strip().isdigit()]
    return partition_info


def parse_list_consumer_groups(output: str) -> Dict:
    """解析 kafka-consumer-groups.sh --list 的输出"""
    lines = [line.strip() for line in output.strip().splitlines() if line.strip()]
    return {"groups": lines, "count": len(lines)}


def parse_describe_consumer_group(output: str) -> Dict:
    """解析 kafka-consumer-groups.sh --describe --group 的输出"""
    lines = output.strip().splitlines()
    result = {"group": "", "state": "", "members": []}

    # 跳过空行和表头行
    header_found = False

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # 检测 GROUP 信息行
        if line_stripped.startswith("GROUP") and "STATE" in line_stripped and not header_found:
            # 这是组概览表头
            continue
        if line_stripped.startswith("Consumer group") and "state:" in line_stripped.lower():
            # Consumer group 'xxx' has no active members. / is ... state: ...
            continue

        # 检测成员详情表头: TOPIC  PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG  CONSUMER-ID  HOST  CLIENT-ID
        if "TOPIC" in line_stripped and "PARTITION" in line_stripped and "CURRENT-OFFSET" in line_stripped:
            header_found = True
            continue

        # 解析数据行
        if header_found:
            fields = line_stripped.split()
            if len(fields) >= 6:
                member = {
                    "topic": fields[0],
                }
                try:
                    member["partition"] = int(fields[1])
                except ValueError:
                    member["partition"] = fields[1]
                try:
                    member["current_offset"] = int(fields[2])
                except ValueError:
                    member["current_offset"] = fields[2]
                try:
                    member["log_end_offset"] = int(fields[3])
                except ValueError:
                    member["log_end_offset"] = fields[3]
                try:
                    member["lag"] = int(fields[4])
                except ValueError:
                    member["lag"] = fields[4]
                if len(fields) >= 7:
                    member["consumer_id"] = fields[5]
                if len(fields) >= 8:
                    member["host"] = fields[6]
                if len(fields) >= 9:
                    member["client_id"] = fields[7]
                result["members"].append(member)

    return result


def parse_config_output(output: str, entity_type: str, entity_name: str) -> Dict:
    """
    解析 kafka-configs.sh --describe 的输出。

    输出格式示例:
    Configs for topic 'test' are retention.ms=86400000,cleanup.policy=delete
    """
    result = {"entity_type": entity_type, "entity_name": entity_name, "configs": {}}

    for line in output.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        # 匹配 "Configs for ... are ..." 格式
        if "Configs for" in line and " are " in line:
            config_part = line.split(" are ", 1)[1].strip()
            if config_part:
                for kv in config_part.split(","):
                    kv = kv.strip()
                    if "=" in kv:
                        k, v = kv.split("=", 1)
                        result["configs"][k.strip()] = v.strip()

    return result


def parse_broker_api_versions(output: str) -> List[Dict]:
    """
    解析 kafka-broker-api-versions.sh 的输出。

    输出格式示例:
    broker1.example.com:9092 (id: 0 rack: null) -> (
        ...API versions...
    )
    """
    import re

    brokers = []
    for line in output.strip().splitlines():
        # 匹配: host:port (id: N rack: xxx) ->
        match = re.match(r"^(\S+):(\d+)\s+\(id:\s*(\d+)\s+rack:\s*(\S+)\)", line)
        if match:
            brokers.append(
                {
                    "host": match.group(1),
                    "port": int(match.group(2)),
                    "id": int(match.group(3)),
                    "rack": match.group(4) if match.group(4) != "null" else None,
                }
            )
    return brokers


def parse_under_replicated_partitions(output: str) -> List[Dict]:
    """解析 kafka-topics.sh --describe --under-replicated-partitions 的输出"""
    return _parse_partition_lines(output)


def parse_unavailable_partitions(output: str) -> List[Dict]:
    """解析 kafka-topics.sh --describe --unavailable-partitions 的输出"""
    return _parse_partition_lines(output)


def _parse_partition_lines(output: str) -> List[Dict]:
    """解析 kafka-topics.sh --describe 过滤后的分区行"""
    partitions = []
    for line in output.strip().splitlines():
        line = line.strip()
        if not line or not line.startswith("Topic:"):
            continue
        if "Partition:" not in line:
            continue

        info = {}
        parts = line.split("\t")
        for part in parts:
            part = part.strip()
            if part.startswith("Topic:"):
                info["topic"] = part.split(":", 1)[1].strip()
            elif part.startswith("Partition:"):
                try:
                    info["partition"] = int(part.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif part.startswith("Leader:"):
                try:
                    info["leader"] = int(part.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif part.startswith("Replicas:"):
                replica_str = part.split(":", 1)[1].strip()
                info["replicas"] = [int(r) for r in replica_str.split(",") if r.strip().isdigit()]
            elif part.startswith("Isr:"):
                isr_str = part.split(":", 1)[1].strip()
                info["isr"] = [int(r) for r in isr_str.split(",") if r.strip().isdigit()]
        if info:
            partitions.append(info)
    return partitions
