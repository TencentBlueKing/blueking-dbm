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
from abc import ABC

import pymysql
from django.db import transaction

from backend import env
from backend.components import DBConfigApi, DBPrivManagerApi
from backend.components.dbconfig.constants import LevelName, OpType, ReqType
from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta.enums import ClusterType
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, ClusterEntry, ProxyInstance, StorageInstance
from backend.utils.string import base64_encode


class ClusterHandler(ABC):
    # 「必须」 集群类型
    cluster_type = None

    def __init__(self, bk_biz_id: int, cluster_id: int):
        self.bk_biz_id = bk_biz_id
        self.cluster_id = cluster_id
        try:
            self.cluster: Cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(cluster_id=cluster_id)

    @classmethod
    def get_exact_handler(cls, bk_biz_id: int, cluster_id: int):
        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(cluster_type="", cluster_id=cluster_id)
        for subclass in cls.__subclasses__():
            if subclass.cluster_type == cluster.cluster_type:
                return subclass(bk_biz_id=bk_biz_id, cluster_id=cluster_id)

    @classmethod
    @transaction.atomic
    def create(cls, *args, **kwargs):
        """「必须」创建集群"""
        raise NotImplementedError

    @classmethod
    @transaction.atomic
    def import_meta(cls, details):
        """「必须」导入元数据"""
        # [*必须] 导入集群数据
        cluster_info = details["cluster_info"]
        cluster_obj = Cluster.objects.create(**cluster_info)
        for cluster_entry in details.get("cluster_entries", []):
            ClusterEntry.objects.create(
                cluster=cluster_obj,
                # 默认导入的访问入口都是 DNS
                cluster_entry_type=cluster_entry["cluster_entry_type"],
                access_port=cluster_entry["access_port"],
                entry=cluster_entry["entry"],
                creator=cluster_obj.creator,
            )

        # [可选] 导入实例数据
        storage_instances = details.get("storage_instances", [])
        storage_instance_objs = [StorageInstance(**storage_instance) for storage_instance in storage_instances]
        StorageInstance.objects.bulk_create(storage_instance_objs, batch_size=100)
        proxy_instances = details.get("proxy_instances", [])
        proxy_instance_objs = [ProxyInstance(**proxy_instance) for proxy_instance in proxy_instances]
        ProxyInstance.objects.bulk_create(proxy_instance_objs, batch_size=100)

        # [可选] 关联存储实例元组对

        # [可选] 实例化集群配置（dbconfig）
        db_configs = details.get("db_configs", [])
        for db_config in db_configs:
            conf_items = [
                {"conf_name": conf_name, "conf_value": conf_value, "op_type": OpType.UPDATE}
                for conf_name, conf_value in db_config["config_map"].items()
            ]

            DBConfigApi.upsert_conf_item(
                {
                    "conf_file_info": {
                        "conf_file": db_config["conf_file"],
                        "conf_type": db_config["conf_type"],
                        "namespace": db_config["namespace"],
                    },
                    "conf_items": conf_items,
                    "bk_biz_id": cluster_obj.bk_biz_id,
                    "level_name": LevelName.CLUSTER.value,
                    "level_value": cluster_obj.immute_domain,
                    "confirm": 0,
                    "req_type": ReqType.SAVE_AND_PUBLISH,
                }
            )

        # [可选] 导入账号信息（dbpriv）
        account = details.get("account")
        if account:
            DBPrivManagerApi.modify_password(
                params={
                    "instances": [
                        {
                            "ip": instance.get("domain") or instance.get("ip"),
                            "port": instance.get("port", cluster_info.get("access_port")),
                            "bk_cloud_id": instance.get("bk_cloud_id", DEFAULT_BK_CLOUD_ID),
                        }
                        for instance in account["instances"]
                    ],
                    "password": base64_encode(account["password"]),
                    "username": account["username"],
                    "component": account["component"],
                    "operator": account.get("operator"),
                }
            )
            # 对 mysql 进行授权，添加 drs 超级账号，TODO：放到子类实现
            if cluster_obj.cluster_type == ClusterType.MySQLOnK8S:

                # 数据库连接配置
                db_config = {
                    "host": cluster_obj.immute_domain,
                    "user": account["username"],
                    "password": account["password"],
                    "database": "mysql",
                }

                # SQL 语句，创建用户并授权
                create_user = "CREATE USER IF NOT EXISTS %s@%s IDENTIFIED WITH mysql_native_password BY %s ;"
                grant_statement = "GRANT ALL PRIVILEGES ON *.* TO %s@%s WITH GRANT OPTION ;"

                # 连接到MySQL
                connection = pymysql.connect(**db_config)

                try:
                    with connection.cursor() as cursor:
                        for host in env.DEFAULT_CLOUD_DRS_ACCESS_HOSTS:
                            # 执行语句
                            cursor.execute(create_user, (env.DRS_USERNAME, host, env.DRS_PASSWORD))
                            cursor.execute(grant_statement, (env.DRS_USERNAME, host))
                    # 提交更改
                    connection.commit()
                finally:
                    # 关闭连接
                    connection.close()

        # [可选] CMDB 标准化，使得能自动下发监控/日志采集配置

        # [可选] 集群实例标准化

    @transaction.atomic
    def decommission(self):
        """「必须」下架集群"""
        raise NotImplementedError

    def topo_graph(self):
        """「必须」提供集群关系拓扑图"""
        raise NotImplementedError
