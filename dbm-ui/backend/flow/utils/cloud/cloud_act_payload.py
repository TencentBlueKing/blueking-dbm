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

from django.utils.translation import ugettext as _

from backend import env
from backend.configuration.models import SystemSettings
from backend.core.encrypt.constants import RSAConfigType
from backend.core.encrypt.handlers import RSAHandler
from backend.db_proxy.constants import NGINX_PUSH_TARGET_PATH, ExtensionType
from backend.flow.consts import (
    CLOUD_NGINX_DBM_DEFAULT_PORT,
    CLOUD_NGINX_MANAGE_DEFAULT_HOST,
    CloudDBHATypeEnum,
    CloudServiceConfFileEnum,
    CloudServiceName,
)
from backend.flow.engine.exceptions import ServiceDoesNotApply


class CloudServiceActPayload(object):
    """
    定义服务不同的执行类型，拼接不同的payload参数，对应不同的dict结构体
    """

    def __init__(self, ticket_data: dict, kwargs: dict):
        self.cloud_id = kwargs["bk_cloud_id"]
        self.kwargs = kwargs
        self.ticket_data = ticket_data

    def __get_drs_ip_port(self):
        drs_apply_details = self.ticket_data["drs"]["host_infos"]
        if not drs_apply_details:
            raise ServiceDoesNotApply(_("单据中不包含DRS的部署信息"))

        drs_ip_port_list = [f"{drs['ip']}:{drs['drs_port']}" for drs in drs_apply_details]
        return drs_ip_port_list

    def __get_dns_ip(self):
        dns_apply_details = self.ticket_data["dns"]["host_infos"]
        if not dns_apply_details:
            raise ServiceDoesNotApply(_("DNS服务未部署，请在DNS服务部署后再进行该服务的部署"))

        dns_ip_list = [dns["ip"] for dns in dns_apply_details]
        return dns_ip_list

    def __get_nginx_internal_domain(self):
        nginx_apply_details = self.ticket_data["nginx"]["host_infos"]
        if not nginx_apply_details:
            raise ServiceDoesNotApply(_("Nginx服务未部署，请在Nginx服务部署后再进行该服务的部署"))

        # TODO: 目前nginx只支持部署一个机器
        nginx_internal_domain = nginx_apply_details[0]["ip"]
        return nginx_internal_domain

    def __generate_service_token(self, service_type: CloudServiceName):
        # 生成透传接口校验的秘钥
        db_cloud_token = f"{self.cloud_id}_{service_type}_token"
        rsa = RSAHandler.get_or_generate_rsa_in_db(RSAConfigType.PROXYPASS.value)
        return RSAHandler.encrypt_password(rsa.rsa_public_key.content, db_cloud_token)

    def get_nginx_apply_payload(self):
        # 现在默认不支持批量部署nginx
        drs_ip_port_list = self.__get_drs_ip_port()
        indent = " " * 8
        format_nginx_drs_server = f"\n{indent}".join([f"server {ip_port};" for ip_port in drs_ip_port_list])

        host = self.kwargs["exec_ip"]
        return {
            "nginx_internal_domain": host["ip"],
            "nginx_external_domain": host["bk_outer_ip"],
            "manage_port": host.get("manage_port", CLOUD_NGINX_MANAGE_DEFAULT_HOST),
            "dbm_port": host.get("dbm_port", CLOUD_NGINX_DBM_DEFAULT_PORT),
            "dbm_momain": env.DBM_EXTERNAL_ADDRESS.replace("https", "http"),
            "upstream_drs_server": format_nginx_drs_server,
            "nginx_child_conf": NGINX_PUSH_TARGET_PATH,
        }

    def get_nginx_reduce_payload(self):
        return {}

    def get_dns_apply_payload(self):
        return {}

    def get_dns_pull_crond_conf_payload(self):
        db_cloud_token = self.__generate_service_token(service_type=CloudServiceName.DNS.value)
        return {
            "nginx_domain": self.__get_nginx_internal_domain(),
            "db_cloud_token": db_cloud_token,
            "bk_cloud_id": self.cloud_id,
        }

    def get_dns_flush_payload(self):
        return {"dns_ips": self.kwargs["dns_ips"], "flush_type": self.kwargs["flush_type"]}

    def get_dns_reduce_payload(self):
        return {}

    def get_dbha_conf_payload(self):
        db_cloud_token = self.__generate_service_token(service_type=CloudServiceName.DBHA.value)
        bkm_dbm_report = SystemSettings.get_setting_value(key="BKM_DBM_REPORT")
        return {
            "db_cloud_token": db_cloud_token,
            "cloud": self.cloud_id,
            "city": self.kwargs["exec_ip"]["bk_city_code"],
            "campus": self.kwargs["exec_ip"]["bk_city_name"],
            "nginx_domain": self.kwargs["nginx_internal_domain"],
            "dbha_user": self.kwargs["plain_user"],
            "dbha_password": self.kwargs["plain_pwd"],
            "mysql_crond_metrics_data_id": bkm_dbm_report["metric"]["data_id"],
            "mysql_crond_metrics_data_token": bkm_dbm_report["metric"]["token"],
            "mysql_crond_agent_address": env.MYSQL_CROND_AGENT_ADDRESS,
            "mysql_crond_beat_path": env.MYSQL_CROND_BEAT_PATH,
        }

    def get_dbha_apply_payload(self):
        return {"dbha_conf": self.kwargs["conf_file_name"], "dbha_type": self.kwargs["dbha_type"]}

    def get_dbha_gm_reduce_payload(self):
        return {"dbha_conf": CloudServiceConfFileEnum.HA_GM.lower(), "dbha_type": CloudDBHATypeEnum.GM.lower()}

    def get_dbha_agent_reduce_payload(self):
        return {"dbha_conf": CloudServiceConfFileEnum.HA_AGENT.lower(), "dbha_type": CloudDBHATypeEnum.AGENT.lower()}

    def get_drs_env_conf_payload(self):
        dns_nameserver = [f"nameserver {ip}" for ip in self.__get_dns_ip()]
        # 格式转义为:
        # nameserver 127.0.0.1\
        # nameserver 127.0.0.2\
        # ...
        # nameserver 127.0.0.n
        dns_nameserver_str = "\\\n".join(dns_nameserver)
        return {
            "drs_port": self.kwargs["exec_ip"]["drs_port"],
            "drs_user": self.kwargs["plain_user"],
            "drs_password": self.kwargs["plain_pwd"],
            "dns_nameserver": dns_nameserver_str,
        }

    def get_drs_apply_paylaod(self):
        return {}

    def get_drs_reduce_payload(self):
        return {}

    def privilege_flush_payload(self):
        return {"access_hosts": self.kwargs["access_hosts"], "user": self.kwargs["user"], "pwd": self.kwargs["pwd"]}
