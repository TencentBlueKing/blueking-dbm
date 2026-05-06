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
from backend.dbm_aiagent.mcp_tools.redis.impl.get_source_access_impl import generate_cluster_query_report


def generate_mongodb_cluster_query_report(job_log_resp, cluster_domain: str, cluster_all_ips: list):
    """复用 Redis 访问来源报告生成逻辑（StorageInstance/ProxyInstance 通用）"""
    tcp_report = generate_cluster_query_report(job_log_resp, cluster_domain, cluster_all_ips)
    return tcp_report
