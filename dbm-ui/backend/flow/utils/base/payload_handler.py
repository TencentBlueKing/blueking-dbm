"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import base64
import logging
from typing import Dict

from django.utils.translation import gettext as _

from backend import env
from backend.components import DBConfigApi, DBPrivManagerApi
from backend.components.dbconfig.constants import FormatType, LevelName, ReqType
from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_proxy.constants import ExtensionType
from backend.db_proxy.models import DBExtension
from backend.db_services.ipchooser.constants import DEFAULT_CLOUD
from backend.flow.consts import DEFAULT_INSTANCE, ConfigTypeEnum, LevelInfoEnum, MySQLPrivComponent, UserName
from backend.flow.utils.mysql.get_mysql_sys_user import generate_mysql_tmp_user
from backend.ticket.constants import TicketType
from backend.utils.string import base64_encode

apply_list = [
    TicketType.MYSQL_SINGLE_APPLY.value,
    TicketType.MYSQL_HA_APPLY.value,
    TicketType.TENDBCLUSTER_APPLY.value,
]

logger = logging.getLogger("flow")


class PayloadHandler(object):
    def __init__(self, bk_cloud_id: int, ticket_data: dict, cluster: dict, cluster_type: str = None):
        """
        @param bk_cloud_id 操作的云区域
        @param ticket_data 单据信息
        @param cluster 需要操作的集群信息
        @param cluster_type 表示操作的集群类型，会决定到db_config获取配置的空间
        """
        self.bk_cloud_id = bk_cloud_id
        self.ticket_data = ticket_data
        self.cluster = cluster
        self.cluster_type = cluster_type
        self.account = self.get_mysql_account()
        self.proxy_account = self.get_proxy_account()

        if self.ticket_data.get("module"):
            self.db_module_id = self.ticket_data["module"]
        elif self.cluster and self.cluster.get("db_module_id"):
            self.db_module_id = self.cluster["db_module_id"]
        else:
            self.db_module_id = 0

    @staticmethod
    def get_proxy_account():
        """
        获取proxy实例内置帐户密码
        """
        data = DBPrivManagerApi.get_password(
            {
                "instances": [DEFAULT_INSTANCE],
                "users": [{"username": UserName.PROXY.value, "component": MySQLPrivComponent.PROXY.value}],
            }
        )["items"]
        return {
            "proxy_admin_pwd": base64.b64decode(data[0]["password"]).decode("utf-8"),
            "proxy_admin_user": data[0]["username"],
        }

    @staticmethod
    def get_tbinlogdumper_account():
        """
        获取tbinlogdumper实例内置帐户密码
        """
        data = DBPrivManagerApi.get_password(
            {
                "instances": [DEFAULT_INSTANCE],
                "users": [{"username": UserName.ADMIN.value, "component": MySQLPrivComponent.TBINLOGDUMPER.value}],
            }
        )["items"]
        return {
            "tbinlogdumper_admin_pwd": base64.b64decode(data[0]["password"]).decode("utf-8"),
            "tbinlogdumper_admin_user": data[0]["username"],
        }

    def get_mysql_account(self) -> dict:
        """
        获取mysql实例内置帐户密码
        """
        user_map = {}
        value_to_name = {member.value: member.name.lower() for member in UserName}
        data = DBPrivManagerApi.get_password(
            {
                "instances": [DEFAULT_INSTANCE],
                "users": [
                    {"username": UserName.BACKUP.value, "component": MySQLPrivComponent.MYSQL.value},
                    {"username": UserName.MONITOR.value, "component": MySQLPrivComponent.MYSQL.value},
                    {"username": UserName.MONITOR_ACCESS_ALL.value, "component": MySQLPrivComponent.MYSQL.value},
                    {"username": UserName.OS_MYSQL.value, "component": MySQLPrivComponent.MYSQL.value},
                    {"username": UserName.REPL.value, "component": MySQLPrivComponent.MYSQL.value},
                    {"username": UserName.YW.value, "component": MySQLPrivComponent.MYSQL.value},
                ],
            }
        )
        for user in data["items"]:
            user_map[value_to_name[user["username"]] + "_user"] = (
                "MONITOR" if user["username"] == UserName.MONITOR_ACCESS_ALL.value else user["username"]
            )
            user_map[value_to_name[user["username"]] + "_pwd"] = base64.b64decode(user["password"]).decode("utf-8")

        if self.ticket_data.get("ticket_type", None) in apply_list:
            # 部署类单据临时给个ADMIN初始化账号密码，部署完成会完成随机化
            user_map["admin_user"] = "ADMIN"
        else:
            # 获取非部署类单据的临时账号作为这次的ADMIN账号
            user_map["admin_user"] = generate_mysql_tmp_user(self.ticket_data["job_root_id"])

        # 用job的root_id 作为这次的临时密码
        user_map["admin_pwd"] = self.ticket_data["job_root_id"]

        return user_map

    @staticmethod
    def get_extension_super_account(bk_cloud_id: int, extension_type: ExtensionType) -> Dict[str, str]:
        """获取扩展服务超级账号"""
        # 若已部署，则从数据库中读取返回
        extension = DBExtension.get_latest_extension(bk_cloud_id=bk_cloud_id, extension_type=extension_type)
        cipher_cloud_name = AsymmetricCipherConfigType.get_cipher_cloud_name(bk_cloud_id)
        if extension:
            return {
                "access_hosts": DBExtension.get_extension_access_hosts(
                    bk_cloud_id=bk_cloud_id, extension_type=extension_type
                ),
                "pwd": AsymmetricHandler.decrypt(name=cipher_cloud_name, content=extension.details["pwd"]),
                "user": AsymmetricHandler.decrypt(name=cipher_cloud_name, content=extension.details["user"]),
            }
        # 若未部署相关扩展服务，且非直连区域，则要求进行部署
        if bk_cloud_id != DEFAULT_CLOUD:
            raise Exception(_("此云区域(bk_cloud_id:{})未部署相关套件{}".format(bk_cloud_id, extension_type)))

        # 直连区域，考虑是容器化部署的通过环境变量获取
        if extension_type == ExtensionType.DRS:
            return {
                "access_hosts": env.DEFAULT_CLOUD_DRS_ACCESS_HOSTS,
                "user": env.DRS_USERNAME,
                "pwd": env.DRS_PASSWORD,
            }
        elif extension_type == ExtensionType.DBHA:
            return {
                "access_hosts": env.DEFAULT_CLOUD_DBHA_ACCESS_HOSTS,
                "user": env.DBHA_USERNAME,
                "pwd": env.DBHA_PASSWORD,
            }
        else:
            raise NotImplementedError(_("不支持{}类型扩展的账号获取").format(extension_type))

    def get_super_account(self):
        """
        获取mysql机器系统管理账号信息
        """
        drs_account_data = self.get_extension_super_account(self.bk_cloud_id, ExtensionType.DRS)
        dbha_account_data = self.get_extension_super_account(self.bk_cloud_id, ExtensionType.DBHA)
        return drs_account_data, dbha_account_data

    @staticmethod
    def redis_get_cluster_pass_from_dbconfig(cluster: Cluster):
        def _redis_get_cluster_config(conf_file, conf_type):
            config = DBConfigApi.query_conf_item(
                params={
                    "bk_biz_id": str(cluster.bk_biz_id),
                    "level_name": LevelName.CLUSTER.value,
                    "level_value": cluster.immute_domain,
                    "level_info": {"module": str(cluster.db_module_id)},
                    "conf_file": conf_file,
                    "conf_type": conf_type,
                    "namespace": cluster.cluster_type,
                    "format": FormatType.MAP,
                }
            )
            return config.get("content", {})

        proxy_conf = _redis_get_cluster_config(cluster.proxy_version, ConfigTypeEnum.ProxyConf)
        redis_conf = _redis_get_cluster_config(cluster.major_version, ConfigTypeEnum.DBConf)
        return {
            "redis_password": redis_conf.get("requirepass", ""),
            "redis_proxy_password": proxy_conf.get("password", ""),
            "redis_proxy_admin_password": proxy_conf.get("predixy_admin_passwd", ""),
        }

    @staticmethod
    def redis_get_cluster_password(cluster: Cluster):
        """
        获取redis集群的密码
        - 优先从密码服务中获取
        - 如果密码服务为空,则从dbconfig中获取
        """
        # cluster_port 先全部统一设置为 0,便于DBHA获取密码
        cluster_port = 0
        query_params = {
            "instances": [{"ip": str(cluster.id), "port": cluster_port, "bk_cloud_id": cluster.bk_cloud_id}],
            "users": [
                {"username": UserName.REDIS_DEFAULT.value, "component": MySQLPrivComponent.REDIS_PROXY_ADMIN.value},
                {"username": UserName.REDIS_DEFAULT.value, "component": MySQLPrivComponent.REDIS_PROXY.value},
                {"username": UserName.REDIS_DEFAULT.value, "component": MySQLPrivComponent.REDIS.value},
            ],
        }
        data = DBPrivManagerApi.get_password(query_params)
        ret = {"redis_password": "", "redis_proxy_admin_password": "", "redis_proxy_password": ""}
        for item in data["items"]:
            if (
                item["username"] == UserName.REDIS_DEFAULT.value
                and item["component"] == MySQLPrivComponent.REDIS_PROXY_ADMIN.value
            ):
                ret["redis_proxy_admin_password"] = base64.b64decode(item["password"]).decode("utf-8")
            elif (
                item["username"] == UserName.REDIS_DEFAULT.value
                and item["component"] == MySQLPrivComponent.REDIS_PROXY.value
            ):
                ret["redis_proxy_password"] = base64.b64decode(item["password"]).decode("utf-8")
            elif (
                item["username"] == UserName.REDIS_DEFAULT.value
                and item["component"] == MySQLPrivComponent.REDIS.value
            ):
                ret["redis_password"] = base64.b64decode(item["password"]).decode("utf-8")
        if (
            ret["redis_password"] == ""
            and ret["redis_proxy_password"] == ""
            and ret["redis_proxy_admin_password"] == ""
        ):
            # 密码服务为空,从dbconfig中获取
            ret = PayloadHandler.redis_get_cluster_pass_from_dbconfig(cluster)
        return ret

    @staticmethod
    def redis_get_password_by_cluster_id(cluster_id: int):
        """
        根据集群ID获取redis集群的密码
        """
        cluster = Cluster.objects.get(id=cluster_id)
        return PayloadHandler.redis_get_cluster_password(cluster)

    @staticmethod
    def redis_get_password_by_domain(immute_domain: str):
        """
        根据集群域名获取redis集群的密码
        """
        cluster = Cluster.objects.get(immute_domain=immute_domain)
        return PayloadHandler.redis_get_cluster_password(cluster)

    @staticmethod
    def redis_save_cluster_password(
        cluster_id: int,
        cluster_port: int,
        bk_cloud_id: int,
        redis_password: str = "",
        redis_proxy_password: str = "",
        redis_proxy_admin_password: str = "",
    ):
        """
        存储redis集群的密码到密码服务
        """
        # cluster_port 先全部统一设置为 0,便于DBHA获取密码
        cluster_port = 0
        query_params = {
            "instances": [{"ip": str(cluster_id), "port": cluster_port, "bk_cloud_id": bk_cloud_id}],
            "username": UserName.REDIS_DEFAULT.value,
            "component": "",
            "password": "",
            "operator": "admin",
            "security_rule_name": "",
        }

        if redis_password and (not redis_password.isspace()):
            query_params["component"] = MySQLPrivComponent.REDIS.value
            query_params["password"] = base64_encode(redis_password)
            DBPrivManagerApi.modify_password(params=query_params)

        if redis_proxy_password and (not redis_proxy_password.isspace()):
            query_params["component"] = MySQLPrivComponent.REDIS_PROXY.value
            query_params["password"] = base64_encode(redis_proxy_password)
            DBPrivManagerApi.modify_password(params=query_params)

        if redis_proxy_admin_password and (not redis_proxy_admin_password.isspace()):
            query_params["component"] = MySQLPrivComponent.REDIS_PROXY_ADMIN.value
            query_params["password"] = base64_encode(redis_proxy_admin_password)
            DBPrivManagerApi.modify_password(params=query_params)

        return True

    @staticmethod
    def redis_save_password_by_cluster(
        cluster: Cluster,
        redis_password: str = "",
        redis_proxy_password: str = "",
        redis_proxy_admin_password: str = "",
    ):
        return PayloadHandler.redis_save_cluster_password(
            cluster.id,
            0,
            cluster.bk_cloud_id,
            redis_password,
            redis_proxy_password,
            redis_proxy_admin_password,
        )

    @staticmethod
    def redis_save_password_by_cluster_id(
        cluster_id: int, redis_password: str = "", redis_proxy_password: str = "", redis_proxy_admin_password: str = ""
    ):
        cluster = Cluster.objects.get(id=cluster_id)
        return PayloadHandler.redis_save_cluster_password(
            cluster.id,
            0,
            cluster.bk_cloud_id,
            redis_password,
            redis_proxy_password,
            redis_proxy_admin_password,
        )

    @staticmethod
    def redis_save_password_by_domain(
        immute_domain: str,
        redis_password: str = "",
        redis_proxy_password: str = "",
        redis_proxy_admin_password: str = "",
    ):
        cluster = Cluster.objects.get(immute_domain=immute_domain)
        return PayloadHandler.redis_save_cluster_password(
            cluster.id,
            0,
            cluster.bk_cloud_id,
            redis_password,
            redis_proxy_password,
            redis_proxy_admin_password,
        )

    @staticmethod
    def redis_delete_cluster_password(cluster_id: int, cluster_port: int, bk_cloud_id: int):
        """
        删除redis集群的密码
        """
        delete_params = {
            "instances": [{"ip": str(cluster_id), "port": cluster_port, "bk_cloud_id": bk_cloud_id}],
            "users": [
                {"username": UserName.REDIS_DEFAULT.value, "component": MySQLPrivComponent.REDIS_PROXY_ADMIN.value},
                {"username": UserName.REDIS_DEFAULT.value, "component": MySQLPrivComponent.REDIS_PROXY.value},
                {"username": UserName.REDIS_DEFAULT.value, "component": MySQLPrivComponent.REDIS.value},
            ],
        }
        DBPrivManagerApi.delete_password(delete_params)

    @staticmethod
    def redis_delete_password_by_cluster(cluster: Cluster):
        """
        根据cluster对象,删除redis集群的密码
        """
        PayloadHandler.redis_delete_cluster_password(cluster.id, 0, cluster.bk_cloud_id)

    @staticmethod
    def redis_delete_password_by_immute_domain(immute_domain: str):
        """
        根据域名删除redis集群的密码
        """
        cluster = Cluster.objects.get(immute_domain=immute_domain)
        PayloadHandler.redis_delete_cluster_password(cluster.id, 0, cluster.bk_cloud_id)

    @staticmethod
    def redis_get_os_account() -> dict:
        """
        获取redis os内置帐户密码
        """
        user_map = {}
        data = DBPrivManagerApi.get_password(
            {
                "instances": [DEFAULT_INSTANCE],
                "users": [
                    {"username": UserName.OS_MYSQL.value, "component": MySQLPrivComponent.REDIS.value},
                ],
            }
        )
        for user in data["items"]:
            user_map["os_user"] = user["username"]
            user_map["os_password"] = base64.b64decode(user["password"]).decode("utf-8")
            break
        return user_map

    @staticmethod
    def get_bigdata_user_key(cluster_type: str) -> MySQLPrivComponent:
        # 不支持的集群类型 缺少 返回值
        if cluster_type == ClusterType.Es.value:
            return MySQLPrivComponent.ES_FAKE_USER
        elif cluster_type == ClusterType.Hdfs.value:
            return MySQLPrivComponent.HDFS_FAKE_USER
        elif cluster_type == ClusterType.Influxdb.value:
            return MySQLPrivComponent.INFLUXDB_FAKE_USER
        elif cluster_type == ClusterType.Kafka.value:
            return MySQLPrivComponent.KAFKA_FAKE_USER
        elif cluster_type == ClusterType.Pulsar.value:
            return MySQLPrivComponent.PULSAR_FAKE_USER

    @staticmethod
    def get_bigdata_username_by_cluster(cluster: Cluster, port: int) -> str:
        """
        通过密码服务 获取大数据集群的用户名
        """
        fake_user = PayloadHandler.get_bigdata_user_key(cluster.cluster_type)
        # 用户名存储方式与密码相同，通过约定fake_user获取
        return PayloadHandler.get_bigdata_password_by_cluster(cluster, port, fake_user)

    @staticmethod
    def get_bigdata_password_by_cluster(cluster: Cluster, port: int, username: str) -> str:
        """
        通过密码服务 获取大数据集群单条认证信息(用户名/密码/token等)
        """
        query_params = {
            "instances": [{"ip": cluster.immute_domain, "port": port, "bk_cloud_id": cluster.bk_cloud_id}],
            "users": [
                {"username": username, "component": cluster.cluster_type},
            ],
        }
        data = DBPrivManagerApi.get_password(query_params)
        # 判断密码服务是否有对应item
        if not data["items"]:
            return ""
        else:
            # 默认返回第一个item
            return base64.b64decode(data["items"][0]["password"]).decode("utf-8")

    @staticmethod
    def get_bigdata_auth_by_cluster(cluster: Cluster, port: int) -> dict:
        """
        通过集群实体，集群端口获取用户名密码(仅username+password)
        - 优先从密码服务中获取
        - 如果密码服务为空,则从dbconfig中获取
        """
        auth = {"username": "", "password": ""}
        # 从密码服务获取用户名，若返回空串，则密码服务未存
        username = PayloadHandler.get_bigdata_username_by_cluster(cluster, port)

        # 若获取到用户名, 则获取密码
        if username:
            auth["username"] = username
            auth["password"] = PayloadHandler.get_bigdata_password_by_cluster(cluster, port, username)

        # 判断auth是否有一个为空, 为空则从dbconfig获取
        if not auth["username"] or not auth["password"]:
            logger.error("cannot get auth info from password service")
            cluster_config_data = DBConfigApi.query_conf_item(
                {
                    "bk_biz_id": str(cluster.bk_biz_id),
                    "level_name": LevelName.CLUSTER,
                    "level_value": cluster.immute_domain,
                    "level_info": {"module": LevelInfoEnum.TendataModuleDefault},
                    "conf_file": cluster.major_version,
                    "conf_type": ConfigTypeEnum.DBConf,
                    "namespace": cluster.cluster_type,
                    "format": FormatType.MAP,
                    "method": ReqType.GENERATE_AND_PUBLISH,
                }
            )
            # 无校验 dbconfig返回内容
            auth["username"] = cluster_config_data["content"]["username"]
            auth["password"] = cluster_config_data["content"]["password"]

        return auth
