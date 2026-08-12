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
from typing import Any, Dict

from backend.utils.env import get_type_env

# 没有任何 kafka 配置时的兜底参数，保证 KafkaProducer 仍可构造（进程不因配置缺失而启动失败）
DEFAULT_REVERSE_REPORT_KAFKA_OPTIONS = {"bootstrap_servers": ":9092"}

# 兼容存量环境：JSON 格式的连接参数，解析失败自动回落默认值
REVERSE_REPORT_KAFKA_OPTIONS: Dict[str, Any] = get_type_env(
    key="REVERSE_REPORT_KAFKA_OPTIONS",
    _type=dict,
    default=DEFAULT_REVERSE_REPORT_KAFKA_OPTIONS,
)


def get_csrf_trusted_origins():
    from . import BK_SAAS_HOST, CSRF_TRUSTED_ORIGINS

    # 优先使用 CSRF_TRUSTED_ORIGINS 配置，否则解析访问地址的二级域名进行信任
    if CSRF_TRUSTED_ORIGINS:
        return CSRF_TRUSTED_ORIGINS
    if BK_SAAS_HOST:
        from urllib.parse import urlparse

        secondary_domain = urlparse(BK_SAAS_HOST).hostname.split(".", 1)[1]
        return [f"https://*.{secondary_domain}", f"http://*.{secondary_domain}"]

    print("Warning: If need, Please provide CSRF_TRUSTED_ORIGINS")
    return []


def get_reverse_report_kafka_options() -> dict:
    """组装反向上报 KafkaProducer 连接参数。

    优先使用 externalKafka 渲染的结构化环境变量；存量环境（滚动升级只替换镜像，
    只有 REVERSE_REPORT_KAFKA_OPTIONS 连接串）回落到连接串解析。
    解析失败时降级到默认值并打日志，避免 settings 加载阶段抛异常导致进程无法启动。

    :return: 可直接展开给 kafka.KafkaProducer 的 kwargs
    """
    servers = get_type_env(key="REVERSE_REPORT_KAFKA_BOOTSTRAP_SERVERS", _type=str, default="")
    if servers:
        options = {"bootstrap_servers": [server.strip() for server in servers.split(",") if server.strip()]}
        username = get_type_env(key="REVERSE_REPORT_KAFKA_USERNAME", _type=str, default="")
        if username:
            options.update(
                {
                    "sasl_plain_username": username,
                    "sasl_plain_password": get_type_env(key="REVERSE_REPORT_KAFKA_PASSWORD", _type=str, default=""),
                    "sasl_mechanism": get_type_env(
                        key="REVERSE_REPORT_KAFKA_SASL_MECHANISM", _type=str, default="SCRAM-SHA-512"
                    ),
                    "security_protocol": get_type_env(
                        key="REVERSE_REPORT_KAFKA_SECURITY_PROTOCOL", _type=str, default="SASL_PLAINTEXT"
                    ),
                }
            )
        return options

    return REVERSE_REPORT_KAFKA_OPTIONS
