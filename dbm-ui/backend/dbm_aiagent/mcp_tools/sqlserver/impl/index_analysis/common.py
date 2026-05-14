# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

索引分析功能域 - 子域内共享常量。

通用工具函数已统一下沉到 mcp_tools/sqlserver/helpers/：
    - quote_sqlserver_ident    → helpers.sql_safety
    - resolve_target_instance  → helpers.get_instance_address
    - run_user_db_read         → helpers.rpc_runner
    - build_stats_outdated_sql → helpers.sqlserver_stats

------------------------------------------------------------------
RPC 通道选择规则（与 DRS 后端账号权限一一对应）
------------------------------------------------------------------
- DRSApi.sqlserver_sys_read_rpc
    账号仅对系统库只读：master / msdb / model / tempdb / Monitor。
    用于实例级、不依赖业务库上下文的查询。
- DRSApi.sqlserver_data_read_rpc
    账号对业务库只读 + 已授予 VIEW SERVER STATE。
    本子域所有工具都是"按业务表分析"，目标库始终是业务库，
    因此统一走 sqlserver_data_read_rpc。
"""

# 默认 schema：SQL Server 中绝大多数业务表都在 dbo 下
DEFAULT_SCHEMA = "dbo"
