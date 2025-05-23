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

from dataclasses import dataclass

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta.models import AppCache, Cluster
from backend.flow.consts import ExecuteShellScriptUser, OracleDBActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.utils.oracle.oracle_password import OraclePassword


@dataclass()
class ExecuteScriptActKwargs:
    """节点私有变量数据类"""

    def __init__(self):
        self.payload: dict = None
        self.db_info: list = None
        self.work_path: str = "/data"
        self.app: str = None
        self.manager_user: str = ""
        self.execute_user: str = ""

    @staticmethod
    def get_password(ip: str, port: int, bk_cloud_id: int, username: str) -> str:
        """获取密码"""

        result = OraclePassword().get_password_from_db(ip=ip, port=port, bk_cloud_id=bk_cloud_id, username=username)
        if result["password"] is None:
            raise ValueError(
                "get password of user:{} from password service fail, error:{}".format(username, result["info"])
            )
        return result["password"]

    def get_db_info_by_cluster_id(self):
        """通过cluster_id获取hosts"""

        # 获取app名字
        self.app = AppCache.objects.get(bk_biz_id=self.payload["bk_biz_id"]).db_app_abbr
        # 获取集群信息
        for cluster in self.payload["cluster_info"]:
            cluster_info = Cluster.objects.get(id=cluster["id"])
            domain = cluster_info.immute_domain
            instance = cluster_info.storageinstance_set.filter(instance_inner_role="master")[0]
            self.db_info.append(
                {
                    "ip": instance.machine.ip,
                    "bk_cloud_id": instance.machine.bk_cloud_id,
                    "port": instance.port,
                    "service_name": instance.name,
                    "domain": domain,
                    "execute_db": cluster["execute_db"],
                }
            )

    def get_send_media_kwargs(self):
        """下发原子任务介质的kwargs"""

        return {
            "exec_account": ExecuteShellScriptUser.Root.value,
            "file_list": GetFileList(db_type=DBType.Oracle).oracle_actuator_pkg(),
            "ip_list": self.hosts,
            "exec_ips": [host["ip"] for host in self.hosts],
            "file_target_path": self.work_path + "/install",
        }

    def get_os_init_kwargs(self):
        """os初始化的kwargs"""

        return {
            "os_init": True,
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "exec_account": ExecuteShellScriptUser.Root.value,
            "bk_cloud_id": self.self.hosts[0]["bk_cloud_id"],
            "exec_ip": self.hosts,
            "db_act_template": {
                "action": OracleDBActuatorActionEnum.OsInit,
                "file_path": self.work_path,
                "payload": {},
            },
        }

    def get_create_dir_kwargs(self):
        """创建dbactuator执行目录的kwargs"""

        return {
            "create_dir": True,
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "exec_account": ExecuteShellScriptUser.Root.value,
            "bk_cloud_id": self.payload["hosts"][0]["bk_cloud_id"],
            "exec_ip": self.hosts,
            "db_act_template": {
                "file_path": self.work_path,
                "payload": {},
            },
        }

    def get_send_sql_kwargs(self):
        """获取分发sql文件的kwargs"""

        bk_biz_id = self.payload["bk_biz_id"]
        uid = self.payload["uid"]
        sql_files_full_path_list = [
            "{}/{}/oracle/sqlfile/{}/{}/{}".format(env.BKREPO_PROJECT, env.BKREPO_BUCKET, str(bk_biz_id), uid, file)
            for file in self.payload["script_files"]
        ]
        exec_ips = [host["ip"] for host in self.hosts]
        return {
            "exec_account": ExecuteShellScriptUser.Oracle.value,
            "file_list": sql_files_full_path_list,
            "ip_list": self.hosts,
            "exec_ips": exec_ips,
            "file_target_path": "{}/install/dbactuator-{}".format(self.work_path, uid),
        }

    def get_execute_script_kwargs(self, info: dict) -> dict:
        """获取执行脚本的kwargs"""

        # 获取cluster密码管理员密码 执行脚本用户密码
        manager_user_password = self.get_password(
            ip="0.0.0.0", port=0, bk_cloud_id=info["bk_cloud_id"], username=self.manager_user
        )
        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "exec_account": ExecuteShellScriptUser.Oracle.value,
            "bk_cloud_id": info["bk_cloud_id"],
            "exec_ip": info["ip"],
            "db_act_template": {
                "file_path": self.work_path,
                "payload": {
                    "app": self.app,
                    "taskid": self.payload["uid"],
                    "ip": info["ip"],
                    "port": info["port"],
                    "servicename": info["service_name"],
                    "blurdb": info["execute_db"],
                    "manageruser": "",
                    "manageruserpassword": manager_user_password,
                    "executeuserpassword": "",
                    "scriptfiles": self.payload["script_files"],
                },
            },
        }


@dataclass()
class CommonContext:
    """通用可读写上下文"""

    _data: dict = None

    # 调用第三方接口返回的数据
    def __init__(self):
        self._data = {}
        pass
