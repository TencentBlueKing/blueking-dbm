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
from typing import Dict

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import ConfType, LevelName
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.dbconfig.dataclass import DBBaseConfig, DBConfigLevelData, UpsertConfigData
from backend.db_services.dbconfig.handlers import DBConfigHandler


class UpsertDBConfigItems:
    """
    更新dbconfig的配置项
    用户手动处理集群未生成配置的问题
    """

    def __init__(self, bk_biz_id, cluster_domain, module=-1, db_version="", spider_version=""):
        self.bk_biz_id = bk_biz_id
        self.cluster_domain = cluster_domain
        self.db_module_id = module
        self.db_version = db_version
        self.spider_version = spider_version
        self.cluster_type = ""

        if cluster_domain == "":
            return
        cluster_obj = Cluster.objects.filter(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)[0]
        self.cluster_id = cluster_obj.id
        if self.db_module_id == -1:
            self.db_module_id = cluster_obj.db_module_id
        if not self.cluster_type:
            self.cluster_type = cluster_obj.cluster_type
        if not self.db_version:
            self.db_version = cluster_obj.major_version

    def save_deploy_config(self, charset=""):
        """
        保存部署配置
        """
        conf_items = []
        if charset:
            conf_items.append(
                {
                    "conf_name": "charset",
                    "op_type": "update",
                    "conf_value": charset,
                }
            )
        if self.db_version:
            conf_items.append(
                {
                    "conf_name": "db_version",
                    "op_type": "update",
                    "conf_value": self.db_version,
                }
            )
        if self.cluster_type == ClusterType.TenDBCluster.value and self.spider_version:
            conf_items.append(
                {
                    "conf_name": "spider_version",
                    "op_type": "update",
                    "conf_value": self.spider_version,
                }
            )
        conf_dict = {
            "bk_biz_id": self.bk_biz_id,
            "level_name": LevelName.MODULE.value,
            "level_value": self.db_module_id,
            "confirm": 0,
            "conf_items": conf_items,
            "meta_cluster_type": self.cluster_type,
            "conf_type": ConfType.DEPLOY.value,
            "version": "deploy_info",
        }

        base_conf = DBBaseConfig.from_dict(conf_dict)
        dbconfig_level_data = DBConfigLevelData.from_dict(conf_dict)

        upsert_config_data = UpsertConfigData.from_dict(conf_dict)
        if upsert_config_data.conf_items:
            print(conf_dict)
            DBConfigHandler(base_conf).save_module_deploy_info(dbconfig_level_data, upsert_config_data)

    def generate_config(self, dbconf: Dict, proxyconf: Dict):
        """
        生成集群的 后端 dbconf 和 接入层 proxyconf 的配置
        """
        cluster_conf_dict = {
            "bk_biz_id": self.bk_biz_id,
            "conf_items": [],
            "conf_type": "dbconf",
            "confirm": 0,
            "description": "",
            "level_name": LevelName.CLUSTER.value,
            "level_value": self.cluster_id,  # self.cluster_domain,
            "meta_cluster_type": self.cluster_type,
            "level_info": {
                "module": str(self.db_module_id),
            },
        }

        base_conf = DBBaseConfig.from_dict(cluster_conf_dict)

        # storage layer
        conf_items = []
        for key, value in dbconf.items():
            conf_items.append(
                {
                    "conf_name": key,
                    "op_type": "update",
                    "conf_value": str(value),
                }
            )
        cluster_conf_dict["version"] = self.db_version
        cluster_conf_dict["conf_type"] = "dbconf"
        cluster_conf_dict["conf_items"] = conf_items
        upsert_config_data = UpsertConfigData.from_dict(cluster_conf_dict)
        dbconfig_level_data = DBConfigLevelData.from_dict(cluster_conf_dict)
        if self.db_version and upsert_config_data.conf_items:
            print(cluster_conf_dict)
            DBConfigHandler(base_conf).upsert_level_config(dbconfig_level_data, upsert_config_data)

        # proxy layer
        conf_items = []
        for key, value in proxyconf.items():
            conf_items.append(
                {
                    "conf_name": key,
                    "op_type": "update",
                    "conf_value": str(value),
                }
            )
        cluster_conf_dict["version"] = self.spider_version
        cluster_conf_dict["conf_type"] = "dbconf"  # proxyconf
        cluster_conf_dict["conf_items"] = conf_items
        upsert_config_data = UpsertConfigData.from_dict(cluster_conf_dict)
        dbconfig_level_data = DBConfigLevelData.from_dict(cluster_conf_dict)
        if self.spider_version and upsert_config_data.conf_items:
            print(cluster_conf_dict)
            DBConfigHandler(base_conf).upsert_level_config(dbconfig_level_data, upsert_config_data)

    def save_backup_client_config(self, bk_cloud_id, backup_client_conf: Dict):
        """
        保存备份客户端配置（cosinfo.toml）
        :param bk_cloud_id: 云区域ID
        :param backup_client_conf: 备份客户端配置字典，支持以下字段：
            - region: cos区域，如 "ap-hongkong"
            - bucket_name: cos桶名称
            - secret_id: cos密钥ID
            - secret_key: cos密钥Key
            - endpoint: cos端点地址
            - storage_type: 存储类型
        do not need cluster_domain
        """
        # 配置项名称与 conf_name 的映射关系
        conf_name_map = {
            "storage_type": "cos_auth.storage_type",
            "bucket_name": "cos_auth.bucket_name",
            "region": "cos_auth.region",
            "secret_id": "cos_auth.secret_id",
            "secret_key": "cos_auth.secret_key",
            "endpoint": "cos_auth.endpoint",
        }

        conf_items = []
        for key, value in backup_client_conf.items():
            if key in conf_name_map:
                conf_items.append(
                    {
                        "conf_name": conf_name_map[key],
                        "op_type": "update",
                        "conf_value": str(value),
                    }
                )

        if not conf_items:
            return

        DBConfigApi.save_conf_item(
            {
                "conf_file_info": {"conf_file": "cosinfo.toml", "conf_type": "backup_client", "namespace": "common"},
                "bk_biz_id": str(self.bk_biz_id),
                "level_name": "bk_cloud_id",
                "level_value": str(bk_cloud_id),
                "conf_items": conf_items,
            }
        )
