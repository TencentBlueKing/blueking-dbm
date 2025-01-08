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
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _

from backend.configuration.constants import DBType
from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.handlers import AsymmetricHandler
from blue_krill.data_types.enum import EnumField, StructuredEnum

SWAGGER_TAG = _("透传服务(proxypass)")

NGINX_PUSH_TARGET_PATH = "/usr/local/bkdb/nginx-portable/conf/cluster_service/"

# 缓存inst_id和nginx id，用于回调job，默认缓存时间5min
JOB_INSTANCE_EXPIRE_TIME = 5 * 60
# 定义token过期时间1天，防止废弃的token复用
DB_CLOUD_TOKEN_EXPIRE_TIME = 1 * 24 * 60 * 60


class ExtensionType(str, StructuredEnum):
    """扩展类型枚举"""

    NGINX = EnumField("NGINX", _("nginx 转发服务"))
    DNS = EnumField("DNS", _("域名解析服务"))
    DRS = EnumField("DRS", _("SQL 远程执行服务"))
    DBHA = EnumField("DBHA", _("数据库高可用服务"))
    REDIS_DTS = EnumField("REDIS_DTS", _("Redis DTS服务"))


class ExtensionServiceStatus(str, StructuredEnum):
    """扩展服务状态"""

    RUNNING = EnumField("running", _("running"))
    UNAVAILABLE = EnumField("unavailable", _("unavailable"))
    RESTORING = EnumField("restoring", _("restoring"))


class ClusterServiceType(str, StructuredEnum):
    """集群的扩展服务枚举类型"""

    KIBANA = EnumField("kibana", _("kibana-ES管理端"))
    KAFKA_MANAGER = EnumField("kafka_manager", _("kafka_manager-Kafka管理端"))
    HAPROXY = EnumField("ha_proxy", _("haproxy-HDFS管理端"))
    PULSAR_MANAGER = EnumField("pulsar_manager", _("pulsar_manager管理端"))
    DORIS_MANAGER = EnumField("doris_manager", _("doris_manager管理端"))


class ExtensionAccountEnum(str, StructuredEnum):
    """组件内置账号枚举类型"""

    USER = EnumField("user", _("user"))
    PWD = EnumField("pwd", _("pwd"))
    WEBCONSOLE_USER = EnumField("webconsole_user", _("webconsole_user"))
    WEBCONSOLE_PWD = EnumField("webconsole_pwd", _("webconsole_pwd"))

    @classmethod
    def get_account_map(cls, info):
        """从info中获取存在的账号/密码信息"""
        account = {value: info[value] for value in cls.get_values() if value in info}
        return account

    @classmethod
    def generate_random_account(cls, bk_cloud_id: int):
        """生成随机账号"""
        rsa_cloud_name = AsymmetricCipherConfigType.get_cipher_cloud_name(bk_cloud_id)
        user, password = get_random_string(8), get_random_string(16)
        encrypt_user = AsymmetricHandler.encrypt(name=rsa_cloud_name, content=user)
        encrypt_password = AsymmetricHandler.encrypt(name=rsa_cloud_name, content=password)
        return {"user": user, "password": password, "encrypt_user": encrypt_user, "encrypt_password": encrypt_password}

    @classmethod
    def get_account_info(cls, bk_cloud_id: int, details: dict, u_key: str, p_key: str):
        """获取组件的账号和密码信息"""
        rsa_cloud_name = AsymmetricCipherConfigType.get_cipher_cloud_name(bk_cloud_id)
        encrypt_user, encrypt_password = details[u_key], details[p_key]
        user = AsymmetricHandler.decrypt(name=rsa_cloud_name, content=encrypt_user)
        password = AsymmetricHandler.decrypt(name=rsa_cloud_name, content=encrypt_password)
        return {"user": user, "password": password, "encrypt_user": encrypt_user, "encrypt_password": encrypt_password}


CLUSTER__SERVICE_MAP = {
    DBType.Kafka: ClusterServiceType.KAFKA_MANAGER,
    DBType.Es: ClusterServiceType.KIBANA,
    DBType.Hdfs: ClusterServiceType.HAPROXY,
    DBType.Pulsar: ClusterServiceType.PULSAR_MANAGER,
    DBType.Doris: ClusterServiceType.DORIS_MANAGER,
}
