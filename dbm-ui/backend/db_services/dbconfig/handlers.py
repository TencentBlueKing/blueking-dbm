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
from backend.components.dbconfig.constants import ConfFile, ConfType, FormatType, LevelName, ReqType
from backend.configuration.constants import PLAT_BIZ_ID
from backend.db_meta.models import Cluster, DBModule
from backend.db_services.dbconfig.config_mapping import CLUSTER_VERSION_MODULE, COMPONENT_CONFIG_ITEMS
from backend.db_services.dbconfig.dataclass import (
    DBBaseConfig,
    DBConfigDeployData,
    DBConfigLevelData,
    UpsertConfigData,
)
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper

"""
DBConfig 配置文件相关参数
- namespace       命名空间，cluster_type / db_type，按组件类型判定
- conf_file       配置文件，实体存在，比如Mysql 5.7配置，binlog备份配置，dbbackup 配置
- conf_type       配置类型，配置文件的划分
- conf_names      配置项参数列表
- conf_items      配置项参数列表实际值
- level_name      配置级别，平台/模块/集群
- level_value     配置级别值
- xxx_lc          可读中文
- value_allowed:  值限定范围
- value_type_sub: 值限定类型
"""


class DBConfigHandler:
    # 模板变量: {{port}}
    TEMPLATE_FLAG_STATUS = 2

    def __init__(self, base_data: DBBaseConfig, skip_template_item: bool = False):
        self.conf_type = base_data.conf_type
        self.skip_template_item = skip_template_item
        self.meta_cluster_type = base_data.meta_cluster_type

    def list_config_names(self, version) -> List[Dict[str, str]]:
        """查询配置项列表"""
        config_names = DBConfigApi.list_conf_name(
            {"conf_file": version, "namespace": self.meta_cluster_type, "conf_type": self.conf_type}
        )
        return config_names["conf_names"].values()

    def check_conf_name_exists(self, conf_file: str, conf_name: str) -> Dict[str, bool]:
        """检查配置项是否存在"""
        return DBConfigApi.check_conf_name_exists(
            {
                "conf_file": conf_file,
                "conf_name": conf_name,
                "namespace": self.meta_cluster_type,
                "conf_type": self.conf_type,
            }
        )

    def list_platform_configs(self, conf_file: str = "") -> List[Dict[str, Any]]:
        """查询平台配置"""
        pub_configs = DBConfigApi.list_conf_file(
            {
                "namespace": self.meta_cluster_type,
                "conf_type": self.conf_type,
                "bk_biz_id": PLAT_BIZ_ID,
                "level_name": LevelName.PLAT,
                "conf_file": conf_file,
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

    def list_biz_configs(self, bk_biz_id: int, conf_file: str = "") -> List:
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
                "conf_file": conf_file,
            }
        )
        biz_format_configs = []
        biz_config_versions = []
        for biz_conf in biz_configs:
            biz_format_configs.append(self._format_conf_item(biz_conf))
            biz_config_versions.append(biz_conf["conf_file"])

        pub_configs = self.list_platform_configs(conf_file)
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
        # 对于层级是集群的，直接补充对应的模块信息
        if dbconfig_level_data.level_name == LevelName.CLUSTER:
            cluster = Cluster.objects.get(immute_domain=dbconfig_level_data.level_value)
            dbconfig_level_data.level_info = {"module": str(cluster.db_module_id)}

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
                "level_value": dbconfig_level_data.level_value,
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

        # 对于层级是集群的，直接补充对应的模块信息
        if dbconfig_level_data.level_name == LevelName.CLUSTER:
            cluster = Cluster.objects.get(immute_domain=dbconfig_level_data.level_value)
            dbconfig_level_data.level_info = {"module": str(cluster.db_module_id)}

        level_config = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": dbconfig_level_data.bk_biz_id,
                "conf_file": dbconfig_level_data.version,
                "conf_type": self.conf_type,
                "level_name": dbconfig_level_data.level_name,
                "level_value": dbconfig_level_data.level_value,
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
            # 补充平台配置参数
            self._patch_plat_conf_item(conf_detail, plat_conf_item)
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
            "description": dbconfig["description"],
        }

    @staticmethod
    def _patch_plat_conf_item(conf_detail: Dict, plat_conf_item: Dict) -> Dict:
        conf_detail.update(
            {
                "value_allowed": plat_conf_item.get("value_allowed", ""),
                "value_default": plat_conf_item.get("value_default", ""),
                "need_restart": plat_conf_item.get("need_restart", 0),
                "value_type_sub": plat_conf_item.get("value_type_sub", ""),
                "value_type": plat_conf_item.get("value_type", ""),
                "flag_readonly": plat_conf_item.get("flag_readonly", 1),
                "flag_visible": plat_conf_item.get("flag_visible", 0),
                "flag_encrypt": plat_conf_item.get("flag_encrypt", 0),
                "description": plat_conf_item.get("description", ""),
            }
        )
        return conf_detail

    def get_module_by_id(self, dbconfig_deploy_data: DBConfigDeployData) -> List[Dict]:
        """通过模块id查询部署集配置详情"""
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": dbconfig_deploy_data.bk_biz_id,
                "level_name": LevelName.MODULE,
                "level_value": dbconfig_deploy_data.module_id,
                "conf_file": "deploy_info",
                "conf_type": "deploy",
                "namespace": self.meta_cluster_type,
                "format": FormatType.MAP,
            }
        )["content"]

        return data

    @staticmethod
    def list_conf_name_types() -> Dict[str, List[str]]:
        """
        查询 dbconfig 支持的值类型与子类型定义
        response:
        {"BOOL":["ENUM",""],"FLOAT":["ENUM","","RANGE"],"INT":["ENUM","","RANGE"],"NUMBER":["ENUM","","RANGE"],"STRING":
        ["","STRING","ENUM","ENUMS","BYTES","DURATION","REGEX","JSON","MAP","LIST","GOVALIDATE"]}
        """
        return DBConfigApi.list_conf_name_types()

    @staticmethod
    def validate_conf_items(conf_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        校验配置项定义和值是否合法
        request: ValidateConfItemSerializer
        [
            {
                "op_type": "add",
                "conf_name": "xxxxx",
                "value_default": "x",
                "value_type": "STRING",
                "value_type_sub": "ENUM",
                "value_allowed": "on , off",
                "flag_readonly": 0
            }
        ]
        """
        return DBConfigApi.validate_conf_item(params=conf_items)

    def change_conf_names(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        修改平台配置项定义（新增/更新/删除）
        request: ChangeConfNameSerializer
        {
            "namespace": "x",
            "conf_type": "x",
            "conf_file": "x",
            "conf_names": [
                {
                    "op_type": "add",
                    "conf_name": "",
                    "conf_name_lc": "",
                    "value_default": "",
                    "value_type": "",
                    "value_type_sub": "",
                    "value_allowed": "",
                    "need_restart": 1,
                    "flag_readonly": 0,
                    "flag_locked": 0,
                    "flag_visible": 1,
                    "description"
                }
            ]
        }
        """
        data.update(namespace=self.meta_cluster_type, conf_type=self.conf_type)
        return DBConfigApi.change_plat_config(params=data)

    def list_confname_changes(self, params: Dict[str, Any]) -> Any:
        """
        查询配置项定义的变更历史
        request: ListConfNameChangesSerializer
        {
            "namespace": "x",          # 必填，命名空间
            "conf_type": "x",          # 可选，配置类型
            "conf_file": "x",          # 可选，配置文件
            "conf_name": "x"           # 可选，配置项名称
        }
        """
        params.update(namespace=self.meta_cluster_type)
        if self.conf_type:
            params["conf_type"] = self.conf_type
        return DBConfigApi.list_confname_changes(params)

    def list_confitem_changes(self, params: Dict[str, Any]) -> Any:
        """
        查询集群/业务配置项的变更历史
        request: ListConfItemChangesSerializer
        {
            "bk_biz_id": "x",          # 必填，业务ID
            "namespace": "x",          # 必填，命名空间
            "conf_type": "x",          # 可选，配置类型
            "conf_file": "x",          # 可选，配置文件
            "conf_name": "x",          # 可选，配置项名称
            "level_name": "x",         # 可选，层级名称，如 app、cluster
            "level_value": "x"         # 可选，层级值，如 app123、aa.bb.cc.db
        }
        """
        params.update(namespace=self.meta_cluster_type)
        if self.conf_type:
            params["conf_type"] = self.conf_type
        return DBConfigApi.list_confitem_changes(params)

    def list_conf_types(self) -> List[Dict[str, str]]:
        """
        查询组件支持的配置类型
        """
        conf_type_map = COMPONENT_CONFIG_ITEMS.get(self.meta_cluster_type, {})
        return [{"conf_type": ct, "name": str(ConfType.get_choice_label(ct))} for ct in conf_type_map]

    def list_cluster_module_conf_files(
        self,
        bk_biz_id: int,
        db_module_id: int = None,
        cluster_id: int = None,
        deploy_versions: dict = None,
    ) -> List[Dict[str, str]]:
        """
        查询组件对应模块/集群内支持的配置文件
        """
        if not db_module_id and not cluster_id and not deploy_versions:
            raise ValueError("db_module_id, cluster_id and deploy_versions cannot be all empty")

        conf_type_map = COMPONENT_CONFIG_ITEMS.get(self.meta_cluster_type, {})
        conf_file_values = ConfFile.get_values()
        results = []

        # 获取组件所有的配置文件
        for ct, conf_files in conf_type_map.items():
            for cf in conf_files:
                name = str(ConfFile.get_choice_label(cf)) if cf in conf_file_values else cf
                results.append({"conf_type": ct, "conf_file": cf, "name": name})

        # 重新查询配置版本文件
        base_deploy_params = {
            "bk_biz_id": str(bk_biz_id),
            "namespace": self.meta_cluster_type,
            "conf_type": ConfType.DEPLOY,
            "conf_file": ConfFile.DEPLOY_INFO,
            "level_name": LevelName.MODULE,
            "format": FormatType.MAP,
        }
        if deploy_versions:
            # 新建模块时，版本是用户选择
            deploy_info = deploy_versions
        elif db_module_id:
            # 查询模块级别的部署版本
            base_deploy_params.update({"level_value": str(db_module_id)})
            deploy_info = DBConfigApi.query_conf_item(base_deploy_params)["content"]
        elif cluster_id and self.meta_cluster_type in CLUSTER_VERSION_MODULE:
            # 集群类型为模块级别，则部署版本需要通过模块查询
            db_module_id = Cluster.objects.get(id=cluster_id).db_module_id
            base_deploy_params.update({"level_value": str(db_module_id)})
            deploy_info = DBConfigApi.query_conf_item(base_deploy_params)["content"]
        else:
            # 查询集群获取部署版本
            db_version = Cluster.objects.get(id=cluster_id).major_version
            deploy_info = {"db_version": db_version}

        # 替换部署版本的占位符为真实部署版本
        for cf in results:
            if cf["conf_file"] in ConfFile.get_values():
                continue
            cf["conf_file"] = cf["name"] = deploy_info.get(cf["conf_file"], "")

        return results

    def delete_module_config(self, params: Dict[str, Any]) -> Any:
        """
        删除模块的所有配置项
        request: DeleteModuleConfigSerializer
        {
            "bk_biz_id": "string",
            "db_module_id": "string",
            "namespace": "string"
        }
        """
        params.update(namespace=self.meta_cluster_type)
        resp = DBConfigApi.delete_module_config(params)
        DBModule.objects.filter(db_module_id=params["db_module_id"]).delete()
        return resp

    def recover_default_conf_item(self, params: Dict[str, Any]) -> Any:
        """
        恢复默认值，即删除当前级别的配置，放弃集群的自定义配置，从上级继承
        request: RecoverDefaultConfItemSerializer
        {
            "bk_biz_id": "testapp",
            "conf_file": "MySQL-5.7",
            "conf_names": ["string"],
            "conf_type": "dbconf",
            "level_name": "cluster",
            "level_value": "string",
            "namespace": "tendbha"
        }
        """
        params.update(namespace=self.meta_cluster_type, conf_type=self.conf_type)
        return DBConfigApi.recover_default_conf_item(params)

    def list_level_values(self, bk_biz_id: int, conf_file: str, level_name: str) -> List[Dict]:
        """
        查询配置文件在某个层级下的级别值列表
        request:
        {
            "bk_biz_id": 2005000194,
            "conf_type": "dbconf",
            "conf_file": "MySQL-5.7",
            "level_name": "module",
            "namespace": "tendbha"
        }
        response: [{"bk_biz_id": x, "conf_type": x, "conf_file": x, "level_name": x, "level_value": x}, ...]
        """
        return DBConfigApi.list_level_values(
            {
                "bk_biz_id": bk_biz_id,
                "conf_type": self.conf_type,
                "conf_file": conf_file,
                "level_name": level_name,
                "namespace": self.meta_cluster_type,
            }
        )

    def list_cos_configs(self, bk_biz_id: int) -> List[Dict]:
        """
        查询所有云区域下的COS配置列表
        1. 通过 list_level_values 获取 conf_type=backup_client, conf_file=cosinfo.toml, level_name=bk_cloud_id 下所有 level_value
        2. 逐个调用 get_level_config 获取每个云区域的具体配置
        """
        level_values = self.list_level_values(
            bk_biz_id=bk_biz_id,
            conf_file=ConfFile.COSINFO,
            level_name=LevelName.CLOUD,
        )
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        results = []
        for item in level_values:
            level_data = DBConfigLevelData(
                bk_biz_id=bk_biz_id,
                level_name=LevelName.CLOUD,
                level_value=item["level_value"],
                level_info={},
                version=ConfFile.COSINFO,
            )
            config = self.get_level_config(level_data)
            config["bk_cloud_id"] = item["level_value"]
            config["bk_cloud_name"] = cloud_info[str(config["bk_cloud_id"])]["bk_cloud_name"]
            results.append(config)
        return results

    def delete_level_value(self, params: Dict[str, Any]) -> Any:
        """
        删除某个级别的配置文件
        request: DeleteConfFileLevelSerializer
        {
            "bk_biz_id": 2005000194,
            "conf_type": "dbconf",
            "conf_file": "MySQL-5.7",
            "level_name": "module",
            "level_value": "123",
            "namespace": "tendbha"
        }
        """
        params.update(namespace=self.meta_cluster_type, conf_type=self.conf_type)
        return DBConfigApi.delete_level_value(params)

    def module_clone_query(self, params: Dict[str, str]) -> Any:
        """
        查询集群/业务配置项的变更历史对比
        request: CloneModuleQuerySerializer
        {
              "conf_type": "配置类型",
              "namespace": "集群类型/命名空间",
              "source_bk_biz_id": "源业务ID",
              "source_conf_file": "源配置文件",
              "source_module_id": "源模块ID",
              "target_bk_biz_id": "目标业务ID",
              "target_conf_file": "目标配置文件",
              "target_module_id": "目标模块ID"
        }
        """
        # 查询克隆对比参数
        params.update(namespace=self.meta_cluster_type, conf_type=self.conf_type)
        module_clone_query = DBConfigApi.module_clone_query(params)

        plat_conf_items = DBConfigApi.query_conf_file(
            {
                "conf_file": params["target_conf_file"],
                "conf_type": self.conf_type,
                "namespace": self.meta_cluster_type,
            }
        ).get("conf_names", {})
        # 补充平台级配置
        for conf_name, conf_detail in module_clone_query["content"].items():
            plat_conf_item = plat_conf_items.get(conf_name, {})
            self._patch_plat_conf_item(conf_detail, plat_conf_item)

        return module_clone_query
