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
import shlex
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from django.utils.translation import gettext as _

from backend import env
from backend.components.hadb.client import HADBApi
from backend.db_periodic_task.constants import FailoverDrillVersion
from backend.db_report.models import FailoverDrillReport
from backend.exceptions import AppBaseException
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.deploy_probe_sub_flow import _PROBE_DIR as PROBE_DIR
from backend.flow.engine.bamboo.scene.common.deploy_probe_sub_flow import probe_start_sub_flow
from backend.flow.plugins.components.collections.common.check_resolv_conf import ExecuteShellScriptComponent
from backend.flow.plugins.components.collections.common.failover_status_check import FailoverStatusCheckComponent
from backend.flow.utils.common_act_dataclass import FailoverDrillContext
from backend.flow.utils.failover_drill_dbha import get_dbha_v2_service_ips


class FailoverDrillFlow:
    """
    容灾演练
    通过iptables屏蔽探测触发DBHA切换
    {
        "drill_infos": {
            "bk_biz_id": 3,
            "ticket_type": "REDIS_FAILOVER_DRILL",
            "created_by": "dba",
            "drill_infos": [{  # 演练目标集群和目标IP
                "cluster_id": 7,
                "bk_cloud_id": 1,
                "dbha_version": "v1", # 可选，v1 / v2，缺省为 v1
                "types": ["xxx"], # 可视 cluster_type 而配置
                "xxx": {
                    "ip": "2.2.2.2",
                    "logical_city_id": "17"
                }
            }]
        }
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data
        self.data["uid"] = self.data.get("uid") or self.root_id
        self.uid = self.data["uid"]
        self.hadb_ip_info = set()

    def get_dbha_ip_info(self, db_type: str, bk_cloud_id: int, logical_city_id: int):
        params = {
            "query_args": {"db_type": db_type, "city_id": logical_city_id, "cloud_id": bk_cloud_id},
        }
        agent_ip = self.get_dbha_ip(params=params, name="agent_get_agent_info", module="agent")
        params["query_args"].pop("db_type")
        params["query_args"].pop("city_id")
        gm_ip = self.get_dbha_ip(params=params, name="agent_get_GM_info", module="gm")
        self.hadb_ip_info.update(agent_ip)
        self.hadb_ip_info.update(gm_ip)

    def get_dbha_ip(self, params: dict, name: str, module: str) -> list:
        params["name"] = name
        params["query_args"]["module"] = module
        try:
            hadb_results = HADBApi.ha_status(params=params, raw=True)
        except Exception as e:
            raise AppBaseException(_("hadb-api服务请求失败！{}".format(e)))

        if len(hadb_results["data"]) == 0:
            raise AppBaseException(_("dbha部署gm与agent ip获取异常，请查询dbha gm与agent部署情况"))

        return [info["ip"] for info in hadb_results["data"]]

    def get_add_shell_script(self, exec_info: dict):
        self.get_dbha_ip_info(
            db_type=exec_info["cluster_type"],
            bk_cloud_id=exec_info["bk_cloud_id"],
            logical_city_id=exec_info["logical_city_id"],
        )
        return ";".join(["iptables -I INPUT -s {} -j DROP".format(ip) for ip in self.hadb_ip_info])

    def get_clean_shell_script(self):
        return ";".join(["iptables -D INPUT -s {} -j DROP".format(ip) for ip in self.hadb_ip_info])

    def get_exec_info(self, drill_info: dict, instance_role: str):
        return {
            "cluster_id": drill_info.get("cluster_id"),
            "bk_cloud_id": drill_info.get("bk_cloud_id"),
            "cluster_type": drill_info.get("cluster_type"),
            "root_id": self.root_id,
            "ip": drill_info.get(instance_role).get("ip"),
            "logical_city_id": drill_info.get(instance_role).get("logical_city_id"),
        }

    def report_trigger_time(self, main_task_id, instance_type):
        utc8_timezone = timezone(timedelta(hours=8))
        trigger_time = datetime.now().astimezone(utc8_timezone)
        FailoverDrillReport.objects.filter(main_task_id=main_task_id, instance_type=instance_type).update(
            trigger_dbha_time=trigger_time
        )

    def failover_drill(self):
        pipeline = Builder(root_id=self.root_id, data=self.data)

        sub_pipelines = []
        for drill_info in self.data["drill_infos"]:
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            for role in drill_info.get("types"):
                sub_pipeline.add_sub_pipeline(sub_flow=self._create_sub_pipeline(drill_info, role))
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=(_("容灾演练触发DBHA"))))
        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        pipeline.run_pipeline(is_drop_random_user=True)

    def _create_sub_pipeline(self, drill_info, instance_role):
        """
        创建一个演练流程单元，按 drill_info["dbha_version"] 选择 v1 / v2 动作，缺省为 v1
        """
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        exec_info = self.get_exec_info(drill_info, instance_role)

        if drill_info.get("dbha_version", FailoverDrillVersion.V1.value) == FailoverDrillVersion.V2:
            self._build_v2_acts(sub_pipeline, drill_info, exec_info, instance_role)
        else:
            self._build_v1_acts(sub_pipeline, drill_info, exec_info, instance_role)

        return sub_pipeline.build_sub_process(sub_name=_("容灾演练触发dbha，实例类型：{}".format(instance_role)))

    def _build_v1_acts(self, sub_pipeline: SubBuilder, drill_info: dict, exec_info: dict, instance_role: str):
        """
        1. 在目标主机添加iptables禁用规则屏蔽DBHA agent探测
        2. 监测DBHA切换 或 超时
        3. 恢复目标主机iptables规则
        """
        add_shell_command = self.get_add_shell_script(exec_info=exec_info)
        sub_pipeline.add_act(
            act_name=_("在目标{}添加iptables禁用规则".format(exec_info.get("ip"))),
            act_component_code=ExecuteShellScriptComponent.code,
            kwargs={
                "bk_cloud_id": exec_info.get("bk_cloud_id"),
                "exec_ip": exec_info.get("ip"),
                "cluster": {"shell_command": add_shell_command},
            },
        )

        if "main_task_id" in drill_info:
            self.report_trigger_time(drill_info["main_task_id"], instance_role)

        sub_pipeline.add_act(
            act_name=_("监测DBHA切换状态"),
            act_component_code=FailoverStatusCheckComponent.code,
            kwargs={
                "trans_data_dataclass": FailoverDrillContext.__name__,
                "cloud_id": exec_info.get("bk_cloud_id"),
                "app": str(self.data.get("bk_biz_id")),
                "ip": exec_info.get("ip"),
                "main_task_id": drill_info.get("main_task_id", 0),
                "instance_role": instance_role,
            },
        )

        clean_shell_command = self.get_clean_shell_script()
        sub_pipeline.add_act(
            act_name=_("清理目标{}的iptables禁用规则".format(exec_info.get("ip"))),
            act_component_code=ExecuteShellScriptComponent.code,
            kwargs={
                "bk_cloud_id": exec_info.get("bk_cloud_id"),
                "exec_ip": exec_info.get("ip"),
                "cluster": {"shell_command": clean_shell_command},
            },
        )

    @staticmethod
    def get_v2_trigger_script(service_ips: List[str]) -> str:
        """
        先屏蔽 dbha-v2 服务 IP 再以 mysql 账号停探针：
        - 先停探针会让 SSH 复核连上并判定为"探针没在跑"，只告警不切换
        - stop-probe.sh 只清理当前用户 crontab 中的保活任务，必须以 mysql 执行
        - 停探针失败时回滚本次添加的 iptables 规则
        """
        rollback = "; ".join(["iptables -D INPUT -s {} -j DROP || true".format(shlex.quote(ip)) for ip in service_ips])
        block = "\n".join(["iptables -I INPUT -s {} -j DROP".format(shlex.quote(ip)) for ip in service_ips])
        return f"""#!/bin/bash
set -e
trap '{rollback}' ERR
{block}
su - mysql -c "cd {PROBE_DIR} && ./stop-probe.sh"
"""

    def _build_v2_acts(self, sub_pipeline: SubBuilder, drill_info: dict, exec_info: dict, instance_role: str):
        """
        1. 一个 root 脚本：iptables 屏蔽 dbha-v2 服务 IP + 以 mysql 账号停止探针
        2. 监测 dbha-v2 切换 或 超时
        3. 删除 iptables 规则（需先于启动探针，gen-config 要访问 admin）
        4. 重新生成配置并启动探针
        """
        if not env.ENABLE_DBHA_V2:
            raise AppBaseException(_("ENABLE_DBHA_V2 未开启，无法执行 dbha-v2 容灾演练"))

        bk_cloud_id = exec_info.get("bk_cloud_id")
        exec_ip = exec_info.get("ip")
        service_ips = get_dbha_v2_service_ips(bk_cloud_id, exec_info.get("logical_city_id"))
        if not service_ips:
            raise AppBaseException(_("拿不到 dbha-v2 服务 IP，退出演练"))

        start_probe = probe_start_sub_flow(
            root_id=self.root_id, data=self.data, bk_cloud_id=bk_cloud_id, ips=[exec_ip]
        )
        if start_probe is None:
            raise AppBaseException(_("探针启动子流程生成失败，退出演练"))

        sub_pipeline.add_act(
            act_name=_("在目标{}屏蔽dbha-v2并停止探针".format(exec_ip)),
            act_component_code=ExecuteShellScriptComponent.code,
            kwargs={
                "bk_cloud_id": bk_cloud_id,
                "exec_ip": exec_ip,
                "cluster": {"shell_command": self.get_v2_trigger_script(service_ips)},
            },
        )

        if "main_task_id" in drill_info:
            self.report_trigger_time(drill_info["main_task_id"], instance_role)

        sub_pipeline.add_act(
            act_name=_("监测DBHA切换状态"),
            act_component_code=FailoverStatusCheckComponent.code,
            kwargs={
                "trans_data_dataclass": FailoverDrillContext.__name__,
                "cloud_id": bk_cloud_id,
                "app": str(self.data.get("bk_biz_id")),
                "ip": exec_ip,
                "main_task_id": drill_info.get("main_task_id", 0),
                "instance_role": instance_role,
                "dbha_version": FailoverDrillVersion.V2.value,
            },
        )

        sub_pipeline.add_act(
            act_name=_("清理目标{}的iptables禁用规则".format(exec_ip)),
            act_component_code=ExecuteShellScriptComponent.code,
            kwargs={
                "bk_cloud_id": bk_cloud_id,
                "exec_ip": exec_ip,
                # 规则可能已被 trigger 脚本回滚或重跑时删除，清理失败会阻断后续拉起探针
                "cluster": {
                    "shell_command": "; ".join(
                        ["iptables -D INPUT -s {} -j DROP || true".format(shlex.quote(ip)) for ip in service_ips]
                    )
                },
            },
        )

        sub_pipeline.add_sub_pipeline(sub_flow=start_probe)
