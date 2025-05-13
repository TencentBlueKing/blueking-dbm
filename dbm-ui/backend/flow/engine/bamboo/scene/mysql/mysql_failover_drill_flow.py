"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.components.hadb.client import HADBApi
from backend.exceptions import AppBaseException
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.common.check_resolv_conf import ExecuteShellScriptComponent
from backend.flow.plugins.components.collections.mysql.failover_drill_status_check import FailoverStatusCheckComponent
from backend.flow.utils.mysql.mysql_context_dataclass import FailoverDrillContext


class MysqlFailoverDrill(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data
        self.data["uid"] = self.data.get("uid") or self.root_id
        self.uid = self.data["uid"]
        self.hadb_ip_info = []

    def __get_dbha_ip_info(self, db_type: str, bk_cloud_id: int, logical_city_id: int):
        params = {
            "query_args": {"db_type": db_type, "city_id": logical_city_id, "cloud_id": bk_cloud_id},
        }
        agent_ip = self.__get_dbha_ip(params=params, name="agent_get_agent_info", module="agent")
        params["query_args"].pop("db_type")
        gm_ip = self.__get_dbha_ip(params=params, name="agent_get_GM_info", module="gm")
        self.hadb_ip_info.extend(agent_ip)
        self.hadb_ip_info.extend(gm_ip)

    def __get_dbha_ip(self, params: dict, name: str, module: str) -> list:
        params["name"] = name
        params["query_args"]["module"] = module
        try:
            hadb_results = HADBApi.ha_status(params=params, raw=True)

        except Exception as e:
            raise AppBaseException(_("hadb-api服务请求失败！{}".format(e)))

        if len(hadb_results["data"]) == 0:
            raise AppBaseException(_("dbha部署gm与agent ip获取异常，请查询dbha gm与agent部署情况"))

        return [info["ip"] for info in hadb_results["data"]]

    def __get_add_shell_script(self, exec_info: dict):
        # 返回hadb的ip列表 agent与gm
        self.__get_dbha_ip_info(
            db_type=exec_info["cluster_type"],
            bk_cloud_id=exec_info["bk_cloud_id"],
            logical_city_id=exec_info["logical_city_id"],
        )
        script_list = []
        for ip in self.hadb_ip_info:
            script_list.append("iptables -I INPUT -s {} -j DROP".format(ip))

        return ";".join(script_list)

    def __get_clean_shell_script(self):
        # 返回hadb的ip列表 agent与gm
        script_list = []
        for ip in self.hadb_ip_info:
            script_list.append("iptables -D INPUT -s {} -j DROP".format(ip))

        return ";".join(script_list)

    def __get_exec_info(self, drill_info: dict, instanse_role: str):
        return {
            "cluster_id": drill_info.get("cluster_id"),
            "bk_cloud_id": drill_info.get("bk_cloud_id"),
            "cluster_type": drill_info.get("cluster_type"),
            "root_id": self.root_id,
            "ip": drill_info.get(instanse_role).get("ip"),
            "logical_city_id": drill_info.get(instanse_role).get("logical_city_id"),
        }

    def mysql_failover_drill_flow(self):
        pipeline = Builder(root_id=self.root_id, data=self.data)

        sub_pipelines = []
        for drill_info in self.data["drill_infos"]:
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            sub_pipeline.add_sub_pipeline(sub_flow=self.drill_sub_pipeline(drill_info, drill_info.get("types")[0]))
            sub_pipeline.add_sub_pipeline(sub_flow=self.drill_sub_pipeline(drill_info, drill_info.get("types")[1]))
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("容灾演练触发dbha")))
        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        pipeline.run_pipeline(is_drop_random_user=True)

    def drill_sub_pipeline(self, drill_info, instance_role):
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        # 返回目标执行信息
        exec_info = self.__get_exec_info(drill_info, instance_role)
        add_shell_command = self.__get_add_shell_script(exec_info=exec_info)
        sub_pipeline.add_act(
            act_name=_("向目标{}添加iptables禁用规则".format(exec_info.get("ip"))),
            act_component_code=ExecuteShellScriptComponent.code,
            kwargs={
                "bk_cloud_id": exec_info.get("bk_cloud_id"),
                "exec_ip": exec_info.get("ip"),
                "cluster": {"shell_command": add_shell_command},
            },
        )
        # 根据集群信息，轮询去检查近10分钟dbha的切换状态
        finished_time = datetime.now().astimezone(timezone.utc)
        start_time = finished_time - timedelta(minutes=10)
        sub_pipeline.add_act(
            act_name=_("检查DBHA切换状态"),
            act_component_code=FailoverStatusCheckComponent.code,
            kwargs={
                "trans_data_dataclass": FailoverDrillContext.__name__,
                "cloud_id": exec_info.get("bk_cloud_id"),
                "app": str(self.data.get("bk_biz_id")),
                "ip": exec_info.get("ip"),
                "switch_start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "switch_finished_time": finished_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )

        clean_shell_command = self.__get_clean_shell_script()
        sub_pipeline.add_act(
            act_name=_("向目标{}清理iptables禁用规则".format(exec_info.get("ip"))),
            act_component_code=ExecuteShellScriptComponent.code,
            kwargs={
                "bk_cloud_id": exec_info.get("bk_cloud_id"),
                "exec_ip": exec_info.get("ip"),
                "cluster": {"shell_command": clean_shell_command},
            },
        )

        return sub_pipeline.build_sub_process(sub_name=_("容灾演练触发dbha，实例类型：{}".format(instance_role)))
