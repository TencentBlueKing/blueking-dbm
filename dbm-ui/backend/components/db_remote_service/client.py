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

from django.utils.translation import gettext_lazy as _
from typing_extensions import deprecated

from backend import env
from backend.components.db_remote_service.mysql_replication_compat import (
    get_instance_major_version,
    map_result_fields,
    translate_cmds,
)

from ..domains import DRS_APIGW_DOMAIN
from ..proxy_api import ProxyAPI


class _DRSApi(object):
    MODULE = _("DB 远程服务")
    BASE_DOMAIN = DRS_APIGW_DOMAIN
    # DRS长耗时超时时间为6h TODO: 后续长耗时，改造到下发dbactuator执行更合理
    DRS_TIMEOUT = 6 * 60 * 60
    DRS_SHORT_TIMEOUT = 10

    # SQLServer RPC 默认 connect_timeout（秒）。
    # DRS 后端默认值是 2s，跨云/跨地域链路偶发 "context deadline exceeded"，
    # 这里在客户端侧统一抬高，调用方仍可通过 params["connect_timeout"] 覆盖。
    SQLSERVER_DEFAULT_CONNECT_TIMEOUT = 5

    @classmethod
    def _inject_sqlserver_connect_timeout(cls, params):
        """
        SQLServer RPC 的 before_request 钩子：当调用方未显式传 connect_timeout
        （或传了非正值）时，补上统一的默认值。
        """
        if not isinstance(params, dict):
            return params
        if int(params.get("connect_timeout") or 0) <= 0:
            params["connect_timeout"] = cls.SQLSERVER_DEFAULT_CONNECT_TIMEOUT
        return params

    def __init__(self):
        ssl_flag = True

        # 配置了DRS_SKIP_SSL，或者走容器化方式，认为跳过ssl认证
        if env.DRS_SKIP_SSL:
            ssl_flag = False

        self.rpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="mysql/rpc",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("DB 远程执行, " "8.4+ 版本移除了 slave/master 关键字, 临时替代方案 rpc_mysql_replica_compat"),
            default_timeout=self.DRS_TIMEOUT,
        )

        self.v2_mysql_rpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="v2/mysql/rpc",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("MySQL V2 远程执行, " "8.4+ 版本移除了 slave/master 关键字, 临时替代方案 v2_mysql_rpc_mysql_replica_compat"),
            default_timeout=self.DRS_TIMEOUT,
        )

        self.v2_mysql_ws = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="v2/mysql/ws",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("MySQL V2 远程执行"),
            default_timeout=self.DRS_TIMEOUT,
        )

        self.short_rpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="mysql/rpc",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("DB 远程执行(短耗时)"),
            default_timeout=self.DRS_SHORT_TIMEOUT,
            max_retry_times=1,
        )

        self.v2_short_rpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="v2/mysql/rpc",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("DB 远程执行(短耗时)"),
            default_timeout=self.DRS_SHORT_TIMEOUT,
            max_retry_times=1,
        )

        self.proxyrpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="proxy-admin/rpc",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("DB PROXY远程执行"),
            default_timeout=self.DRS_TIMEOUT,
        )

        self.v2_proxyrpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="v2/proxy-admin/rpc",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("DB PROXY远程执行"),
            default_timeout=self.DRS_TIMEOUT,
        )

        self.redis_rpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="redis/rpc",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("redis 远程执行"),
            default_timeout=self.DRS_TIMEOUT,
        )

        self.twemproxy_rpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="twemproxy/rpc",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("twemproxy 远程执行"),
        )

        self.sqlserver_rpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="sqlserver/rpc",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("sqlserver 远程执行"),
            before_request=self._inject_sqlserver_connect_timeout,
        )

        self.sqlserver_data_read_rpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="sqlserver/data-read-rpc",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("sqlserver 远程执行(业务库数据只读账号)"),
            before_request=self._inject_sqlserver_connect_timeout,
        )

        self.sqlserver_sys_read_rpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="sqlserver/sys-read-rpc",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("sqlserver 远程执行(业务库数据只读账号)"),
            before_request=self._inject_sqlserver_connect_timeout,
        )

        self.webconsole_rpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="webconsole/rpc",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("webconsole 远程执行(只读账号)"),
        )

        self.v2_webconsole_rpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="v2/webconsole/rpc",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("webconsole 远程执行(只读账号)"),
        )

        # {
        #    "payloads": [
        #        {
        #            "addresses": ["1.1.1.1:20000", "2.2.2.2:20002"],
        #            "cmds": ["select 1", "select now()"],
        #            "bk_cloud_id": 0,
        #        },
        #        {
        #            "addresses": ["3.3.3.3:20001", "4.4.4.4:20003"],
        #            "cmds": ["select 2", "select now()"],
        #            "bk_cloud_id": 0,
        #        },
        #    ],
        #    "bk_cloud_id": 0,
        # }
        self.mysql_complex_rpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="mysql/complex-rpc",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("mysql rpc 复杂接口"),
            default_timeout=60 * 3,
        )

        self.v2_mysql_complex_rpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="v2/mysql/complex-rpc",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("mysql rpc 复杂接口"),
            default_timeout=60 * 3,
        )

        self.mongodb_rpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="mongodb/rpc",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("mongodb 远程执行"),
            default_timeout=self.DRS_TIMEOUT,
        )

    @deprecated("this is temporary fix for mysql 8.4 slave/master keyword compatibility")
    def rpc_mysql_replica_compat(self, params, **kwargs):
        """
        MySQL 复制命令专用 RPC 包装方法。

        自动根据目标实例版本翻译复制相关 SQL 命令（如 show slave status → SHOW REPLICA STATUS），
        并将返回结果中的新版字段名映射回旧版字段名（如 Replica_IO_Running → Slave_IO_Running）。

        入参和返回值结构与 DRSApi.rpc 完全一致，调用方只需替换方法名即可。

        内部流程：获取版本 → 翻译 cmds → 调用 self.rpc → 映射返回字段名
        """
        # 获取目标实例版本
        addresses = params.get("addresses", [])
        version = get_instance_major_version(addresses[0]) if addresses else (5, 7)

        # 翻译命令
        original_cmds = params.get("cmds", [])
        translated_cmds, field_map_indices = translate_cmds(original_cmds, version)

        # 构造新的 params（不修改原始 dict）
        new_params = {**params, "cmds": translated_cmds}

        # 调用底层 rpc（ProxyAPI.__call__）
        result = self.rpc(new_params, **kwargs)

        # 映射返回字段名
        if field_map_indices:
            result = map_result_fields(result, field_map_indices)

        return result

    @deprecated("this is temporary fix for mysql 8.4 slave/master keyword compatibility")
    def v2_mysql_rpc_mysql_replica_compat(self, params, **kwargs):
        """
        MySQL V2 复制命令专用 RPC 包装方法。

        逻辑同 rpc_mysql_replica_compat，但使用 self.v2_mysql_rpc。
        """
        # 获取目标实例版本
        addresses = params.get("addresses", [])
        version = get_instance_major_version(addresses[0]) if addresses else (5, 7)

        # 翻译命令
        original_cmds = params.get("cmds", [])
        translated_cmds, field_map_indices = translate_cmds(original_cmds, version)

        # 构造新的 params（不修改原始 dict）
        new_params = {**params, "cmds": translated_cmds}

        # 调用底层 v2_mysql_rpc
        result = self.v2_mysql_rpc(new_params, **kwargs)

        # 映射返回字段名
        if field_map_indices:
            result = map_result_fields(result, field_map_indices)

        return result


DRSApi = _DRSApi()
