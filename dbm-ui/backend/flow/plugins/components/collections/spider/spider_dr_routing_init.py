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

from typing import List, Tuple

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.spider.spider_db_function import parse_servers_by_endpoint

SELECT_SERVERS_SQL = "select Host,Port,Wrapper from mysql.servers"


class SpiderDRRoutingInitService(BaseService):
    """接入层灾难重建：在新中控 primary 上一次性完成路由初始化并下发。

    取代原先 OnlyInitTdbctl / AddAppendDeployInitRouter / TDBCTL FLUSH ROUTING 三个节点。
    与全新部署的 InitMySQLServers 的区别：不 truncate mysql.servers，按下述幂等语义执行：
    - 条目不存在：tdbctl create node
    - 条目已存在且 host/port/wrapper 一致：跳过（重试安全）
    - 条目已存在但 wrapper 冲突：报错并终止，人工介入
    最后 tdbctl enable primary + TDBCTL FLUSH ROUTING，并核对本地路由表完整性。
    仅路由登记，不使用 with database（表结构由后续「从 Remote 同步表结构至中控」负责）。
    """

    def _rpc(
        self, address: str, bk_cloud_id: int, cmds: List[str], log_cmds: List[str] = None, secret: str = ""
    ) -> list:
        self.log_info(f"exec cmds:[{log_cmds or cmds}]")
        res = DRSApi.rpc({"addresses": [address], "cmds": cmds, "force": False, "bk_cloud_id": bk_cloud_id})
        if res[0]["error_msg"]:
            # 错误信息可能回显原始 SQL，先屏蔽密码
            error_msg = res[0]["error_msg"].replace(secret, "xxx") if secret else res[0]["error_msg"]
            raise Exception(f"drs rpc failed: {error_msg}")
        return res[0]["cmd_results"]

    def _query_servers(self, address: str, bk_cloud_id: int) -> dict:
        results = self._rpc(address, bk_cloud_id, ["set tc_admin=1", SELECT_SERVERS_SQL])
        return parse_servers_by_endpoint(results[1]["table_data"])

    def _build_expected(self, kwargs: dict) -> List[Tuple[str, int, str, str]]:
        """预期拓扑：(host, port, wrapper, create_sql)"""
        user, passwd = kwargs["tdbctl_user"], kwargs["tdbctl_pass"]
        spider_port, ctl_port = kwargs["spider_port"], kwargs["ctl_port"]
        expected: List[Tuple[str, int, str, str]] = []
        node_tpl = "tdbctl create node wrapper '{}' options(user '{}', password '{}', host '{}', port {});"
        for ip in kwargs["new_master_ips"]:
            expected.append((ip, ctl_port, "TDBCTL", node_tpl.format("TDBCTL", user, passwd, ip, ctl_port)))
            expected.append((ip, spider_port, "SPIDER", node_tpl.format("SPIDER", user, passwd, ip, spider_port)))
        shard_tpl = "tdbctl create node wrapper '{}' options(user '{}', password '{}', host '{}', port {}, number {});"
        for t in kwargs["remote_tuples"]:
            master_sql = shard_tpl.format("mysql", user, passwd, t["host"], t["port"], t["shard_id"])
            expected.append((t["host"], t["port"], "mysql", master_sql))
            if t.get("slave_host"):
                expected.append(
                    (
                        t["slave_host"],
                        t["port"],
                        "mysql_slave",
                        shard_tpl.format("mysql_slave", user, passwd, t["slave_host"], t["port"], t["shard_id"]),
                    )
                )
        return expected

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        cluster = Cluster.objects.get(id=kwargs["cluster_id"])
        address = kwargs["ctl_primary"]
        passwd = kwargs["tdbctl_pass"]

        expected = self._build_expected(kwargs)
        try:
            existing = self._query_servers(address, cluster.bk_cloud_id)
        except Exception as e:  # pylint: disable=broad-except
            self.log_error(_("查询中控路由表失败: {}").format(e))
            return False

        creates = []
        for host, port, wrapper, sql in expected:
            current = existing.get((host, port))
            if current == wrapper:
                continue
            if current is not None:
                self.log_error(_("路由冲突：{}:{} 已存在 wrapper={}，与期望的 {} 不一致，请人工确认").format(host, port, current, wrapper))
                return False
            creates.append(sql)

        try:
            if creates:
                # 脱敏后打日志
                masked_creates = [c.replace(passwd, "xxx") for c in creates]
                self._rpc(
                    address,
                    cluster.bk_cloud_id,
                    ["set tc_admin=1", *creates, "tdbctl enable primary;"],
                    log_cmds=["set tc_admin=1", *masked_creates, "tdbctl enable primary;"],
                    secret=passwd,
                )
            else:
                self._rpc(address, cluster.bk_cloud_id, ["set tc_admin=1", "tdbctl enable primary;"])
            self._rpc(address, cluster.bk_cloud_id, ["set tc_admin=1", "TDBCTL FLUSH ROUTING"])
        except Exception as e:  # pylint: disable=broad-except
            self.log_error(_("初始化并下发路由失败: {}").format(e))
            return False

        # 结果核对：本地路由表必须包含全部预期条目
        try:
            final = self._query_servers(address, cluster.bk_cloud_id)
        except Exception as e:  # pylint: disable=broad-except
            self.log_error(_("核对路由表失败: {}").format(e))
            return False
        missing = [(h, p, w) for h, p, w, _sql in expected if final.get((h, p)) != w]
        if missing:
            self.log_error(_("路由核对不完整，缺失或不符: {}").format(missing))
            return False

        self.log_info(_("[{}] 初始化并下发接入层路由成功，共 {} 条路由").format(cluster.immute_domain, len(expected)))
        return True


class SpiderDRRoutingInitComponent(Component):
    name = __name__
    code = "spider_dr_routing_init"
    bound_service = SpiderDRRoutingInitService
