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
from typing import Any, Dict, List, Union

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName, ReqType
from backend.configuration.constants import PLAT_BIZ_ID
from backend.db_meta.models import Cluster
from backend.db_services.dbconfig.dataclass import DBBaseConfig, DBConfigLevelData, UpsertConfigData


class DBConfigHandler:
    # 模板变量: {{port}}
    TEMPLATE_FLAG_STATUS = 2

    def __init__(self, base_data: DBBaseConfig, skip_template_item: bool = False):
        self.meta_cluster_type = base_data.meta_cluster_type
        self.conf_type = base_data.conf_type
        self.skip_template_item = skip_template_item

    def list_config_names(self, version) -> List[Dict[str, str]]:
        """查询配置项列表"""
        config_names = DBConfigApi.list_conf_name(
            {"conf_file": version, "namespace": self.meta_cluster_type, "conf_type": self.conf_type}
        )
        return config_names["conf_names"].values()

    def list_platform_configs(self) -> List[Dict[str, Any]]:
        """查询平台配置"""
        pub_configs = DBConfigApi.list_conf_file(
            {
                "namespace": self.meta_cluster_type,
                "conf_type": self.conf_type,
                "bk_biz_id": PLAT_BIZ_ID,
                "level_name": LevelName.PLAT,
            }
        )
        return [self._format_conf_item(conf) for conf in pub_configs]

    def create_platform_config(self, name: str, version: str, upsert_config_data: UpsertConfigData) -> Dict[str, str]:
        """
        namespace,conf_type,conf_file 唯一确定一个配置文件，
        不同DB版本信息体现在 conf_file 里 (如my.cnf#5.6)
        """
        pub_configs = DBConfigApi.add_conf_file(
            {
                "conf_file": version,
                "conf_file_lc": name,
                "conf_names": upsert_config_data.conf_items,
                "conf_type": self.conf_type,
                "confirm": upsert_config_data.confirm,
                "description": upsert_config_data.description,
                "namespace": self.meta_cluster_type,
                "req_type": ReqType.SAVE_AND_PUBLISH,
            }
        )
        return pub_configs

    def upsert_platform_config(self, name: str, version: str, upsert_config_data: UpsertConfigData) -> Dict[str, str]:
        pub_configs = DBConfigApi.update_conf_file(
            {
                "conf_file_info": {
                    "conf_file": version,
                    "conf_file_lc": name,
                    "conf_type": self.conf_type,
                    "description": upsert_config_data.description,
                    "namespace": self.meta_cluster_type,
                },
                "conf_names": upsert_config_data.conf_items,
                "confirm": upsert_config_data.confirm,
                "description": upsert_config_data.publish_description,
                "req_type": ReqType.SAVE_AND_PUBLISH,
            }
        )
        return pub_configs

    def get_platform_config(self, version: str) -> Dict[str, Union[str, List[Dict[str, str]]]]:
        plat_config = DBConfigApi.query_conf_file(
            {
                "conf_file": version,
                "conf_type": self.conf_type,
                "namespace": self.meta_cluster_type,
            }
        )
        level_data = DBConfigLevelData(
            bk_biz_id=PLAT_BIZ_ID, level_name=LevelName.PLAT, level_value=PLAT_BIZ_ID, level_info={}, version=version
        )
        level_config = self.get_level_config(level_data)
        conf_items = plat_config["conf_names"].values()
        level_config["conf_items"] = [
            item
            for item in conf_items
            if self.skip_template_item and item.get("flag_status") != self.TEMPLATE_FLAG_STATUS
        ]
        return level_config

    def list_biz_configs(self, bk_biz_id: int) -> List:
        """
        查询业务配置，优先取业务级配置，若取不到，则取平台配置
        """
        biz_configs = DBConfigApi.list_conf_file(
            {
                "namespace": self.meta_cluster_type,
                "conf_type": self.conf_type,
                "bk_biz_id": bk_biz_id,
                "level_name": LevelName.APP,
                "level_value": bk_biz_id,
            }
        )
        biz_format_configs = []
        biz_config_versions = []
        for biz_conf in biz_configs:
            biz_format_configs.append(self._format_conf_item(biz_conf))
            biz_config_versions.append(biz_conf["conf_file"])

        pub_configs = self.list_platform_configs()
        for pub_conf in pub_configs:
            if pub_conf["version"] not in biz_config_versions:
                pub_conf["is_new"] = True
                biz_format_configs.append(pub_conf)
        return biz_format_configs

    def upsert_level_config(
        self, dbconfig_level_data: DBConfigLevelData, upsert_config_data: UpsertConfigData
    ) -> Dict[str, str]:
        """
        更新层级配置
        """

        # 集群配置统一level_value为domain
        if dbconfig_level_data.level_name == LevelName.CLUSTER:
            cluster = Cluster.objects.get(id=dbconfig_level_data.level_value)
            level_value = cluster.immute_domain
        else:
            level_value = dbconfig_level_data.level_value

        level_config = DBConfigApi.upsert_conf_item(
            {
                "bk_biz_id": dbconfig_level_data.bk_biz_id,
                "conf_file_info": {
                    "conf_file": dbconfig_level_data.version,
                    "conf_type": self.conf_type,
                    "description": upsert_config_data.description,
                    "namespace": self.meta_cluster_type,
                },
                "description": upsert_config_data.publish_description,
                "conf_items": upsert_config_data.conf_items,
                "confirm": upsert_config_data.confirm,
                "level_name": dbconfig_level_data.level_name,
                "level_value": level_value,
                "level_info": dbconfig_level_data.level_info,
                "req_type": ReqType.SAVE_AND_PUBLISH,
            }
        )
        return level_config

    def save_module_deploy_info(
        self, dbconfig_level_data: DBConfigLevelData, upsert_config_data: UpsertConfigData
    ) -> Dict[str, str]:
        """
        保存模块部署配置
        """
        level_config = DBConfigApi.save_conf_item(
            {
                "bk_biz_id": dbconfig_level_data.bk_biz_id,
                "conf_file_info": {
                    "conf_file": dbconfig_level_data.version,
                    "conf_type": self.conf_type,
                    "description": upsert_config_data.description,
                    "namespace": self.meta_cluster_type,
                },
                "conf_items": upsert_config_data.conf_items,
                "level_name": dbconfig_level_data.level_name,
                "level_value": dbconfig_level_data.level_value,
            }
        )
        return level_config

    def get_level_config(
        self, dbconfig_level_data: DBConfigLevelData, fmt=FormatType.LIST
    ) -> Dict[str, Union[str, List[Dict[str, str]]]]:
        """
        查询层级配置
        {
            'bk_biz_id': '2005000194',
            'conf_file': 'REDIS-6',
            'conf_type': 'dbconf',
            'level_name': 'instance',
            'level_value': '112',
            'level_info': {
                'module': '0',
                'cluster': '0',
            },
            'namespace': 'TwemproxyRedisInstance',
            'format': 'list'
        }
        """
        plat_conf_items = DBConfigApi.query_conf_file(
            {
                "conf_file": dbconfig_level_data.version,
                "conf_type": self.conf_type,
                "namespace": self.meta_cluster_type,
            }
        ).get("conf_names", {})

        # 集群配置统一level_value为domain
        if dbconfig_level_data.level_name == LevelName.CLUSTER:
            cluster = Cluster.objects.get(id=dbconfig_level_data.level_value)
            level_value = cluster.immute_domain
        else:
            level_value = dbconfig_level_data.level_value

        level_config = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": dbconfig_level_data.bk_biz_id,
                "conf_file": dbconfig_level_data.version,
                "conf_type": self.conf_type,
                "level_name": dbconfig_level_data.level_name,
                "level_value": level_value,
                "level_info": dbconfig_level_data.level_info,
                "namespace": self.meta_cluster_type,
                "format": fmt,
            }
        )
        conf_file_info = level_config["conf_file_info"]
        conf_items = []
        # 补充平台配置中的 value_allowed、need_restart等字段
        for conf_name, conf_detail in level_config["content"].items():
            plat_conf_item = plat_conf_items.get(conf_name, {})

            # 忽略模板变量{{key}}: flag_status = 2
            if self.skip_template_item and plat_conf_item.get("flag_status") == self.TEMPLATE_FLAG_STATUS:
                continue

            conf_detail.update(
                {
                    "value_allowed": plat_conf_item.get("value_allowed", ""),
                    "need_restart": plat_conf_item.get("need_restart", 0),
                    "value_type_sub": plat_conf_item.get("value_type_sub", ""),
                }
            )
            conf_items.append(conf_detail)

        return {
            "version": conf_file_info["conf_file"],
            "name": conf_file_info["conf_file_lc"],
            "description": conf_file_info["description"],
            "updated_at": conf_file_info["updated_at"],
            "updated_by": conf_file_info["updated_by"],
            "conf_items": conf_items,
        }

    def list_config_version_history(self, dbconfig_level_data: DBConfigLevelData) -> List[Dict]:
        """
        查询配置版本历史
        """
        history = DBConfigApi.list_version(
            {
                "bk_biz_id": dbconfig_level_data.bk_biz_id,
                "conf_file": dbconfig_level_data.version,
                "conf_type": self.conf_type,
                "level_name": dbconfig_level_data.level_name,
                "level_value": dbconfig_level_data.level_value,
                "namespace": self.meta_cluster_type,
            }
        )
        # 兼容 versions 返回为 None 的情况
        history["versions"] = history["versions"] or []
        return history

    def get_config_version_detail(self, dbconfig_level_data: DBConfigLevelData, revision: str) -> Dict:
        """
        查询配置版本历史详情
        """
        conf_detail = self.get_level_config(dbconfig_level_data)
        conf_detail.pop("conf_items")
        version_detail = DBConfigApi.version_detail(
            {
                "bk_biz_id": dbconfig_level_data.bk_biz_id,
                "conf_file": dbconfig_level_data.version,
                "conf_type": self.conf_type,
                "level_name": dbconfig_level_data.level_name,
                "level_value": dbconfig_level_data.level_value,
                "namespace": self.meta_cluster_type,
                "revision": revision,
            }
        )
        version_detail.update(
            {
                "configs": version_detail["configs"].values(),
                "configs_diff": version_detail["configs_diff"].values(),
                "publish_description": version_detail["description"],
                "version": conf_detail["version"],
                "name": conf_detail["name"],
                "description": conf_detail["description"],
            }
        )
        version_detail.update(conf_detail)
        return version_detail

    @staticmethod
    def _format_conf_item(dbconfig: Dict[str, str]) -> Dict[str, str]:
        """将dbconfig的配置转化为统一格式"""
        return {
            "name": dbconfig["conf_file_lc"],
            "version": dbconfig["conf_file"],
            "updated_at": dbconfig["updated_at"],
            "updated_by": dbconfig["updated_by"],
        }
