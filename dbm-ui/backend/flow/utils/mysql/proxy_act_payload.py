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

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_package.models import Package
from backend.flow.consts import ConfigTypeEnum, DBActuatorActionEnum, DBActuatorTypeEnum, MediumEnum, NameSpaceEnum

logger = logging.getLogger("flow")


class ProxyActPayload(object):
    """
    定义proxy不同执行类型，拼接不同的payload参数，对应不同的dict结构体.
    """

    @staticmethod
    def __get_proxy_account():
        """
        获取proxy实例内置帐户密码
        """
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": "0",
                "level_name": LevelName.PLAT,
                "level_value": "0",
                "conf_file": "proxy#user",
                "conf_type": ConfigTypeEnum.InitUser,
                "namespace": NameSpaceEnum.TenDB.value,
                "format": FormatType.MAP,
            }
        )
        return data["content"]

    def __get_proxy_config(self):
        """获取proxy安装配置, 平台层级的配置，没有业务区分"""
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": "0",
                "level_name": LevelName.PLAT,
                "level_value": "0",
                "conf_file": "default",
                "conf_type": "proxyconf",
                "namespace": self.cluster_type,
                "format": FormatType.MAP,
            }
        )
        return data["content"]

    def get_install_proxy_payload(self, **kwargs) -> dict:
        """
        拼接安装proxy的payload参数
        """
        proxy_pkg = Package.get_latest_package(version="latest", pkg_type=MediumEnum.MySQLProxy)
        return {
            "db_type": DBActuatorTypeEnum.Proxy.value,
            "action": DBActuatorActionEnum.Deploy.value,
            "payload": {
                "general": {"runtime_account": self.proxy_account},
                "extend": {
                    "host": kwargs["ip"],
                    "pkg": proxy_pkg.name,
                    "pkg_md5": proxy_pkg.md5,
                    "ports": self.ticket_data.get("proxy_ports", []),
                    "proxy_configs": {"mysql-proxy": self.__get_proxy_config()},
                },
            },
        }

    def get_set_proxy_backends(self, **kwargs) -> dict:
        """
        拼接proxy配置后端实例的payload参数
        """
        set_backend_ip = (
            self.cluster.get("set_backend_ip")
            if self.cluster.get("set_backend_ip")
            else kwargs["trans_data"].get("set_backend_ip")
        )

        return {
            "db_type": DBActuatorTypeEnum.Proxy.value,
            "action": DBActuatorActionEnum.SetBackend.value,
            "payload": {
                "general": {"runtime_account": self.proxy_account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["proxy_port"],
                    "backend_host": set_backend_ip,
                    "backend_port": self.cluster["mysql_port"],
                },
            },
        }

    def get_uninstall_proxy_payload(self, **kwargs) -> dict:
        """
        卸载proxy进程的payload 参数
        """
        return {
            "db_type": DBActuatorTypeEnum.Proxy.value,
            "action": DBActuatorActionEnum.UnInstall.value,
            "payload": {
                "general": {"runtime_account": self.proxy_account},
                "extend": {
                    "host": kwargs["ip"],
                    "force": self.ticket_data["force"],
                    "ports": [self.cluster["proxy_port"]],
                },
            },
        }

    def get_clone_proxy_user_payload(self, **kwargs):
        """
        克隆proxy上的user白名单
        """
        return {
            "db_type": DBActuatorTypeEnum.Proxy.value,
            "action": DBActuatorActionEnum.CloneProxyUser.value,
            "payload": {
                "general": {"runtime_account": self.proxy_account},
                "extend": {
                    "source_proxy_host": kwargs["ip"],
                    "source_proxy_port": self.cluster["proxy_port"],
                    "target_proxy_host": self.cluster["target_proxy_ip"],
                    "target_proxy_port": self.cluster["proxy_port"],
                },
            },
        }

    def get_restart_proxy_payload(self, **kwargs):
        """
        重启proxy
        """
        return {
            "db_type": DBActuatorTypeEnum.Proxy.value,
            "action": DBActuatorActionEnum.RestartProxy.value,
            "payload": {
                "general": {"runtime_account": self.proxy_account},
                "extend": {
                    "host": kwargs["ip"],
                    "port": self.cluster["proxy_port"],
                },
            },
        }
