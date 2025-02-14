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
import glob
import json
import logging
import os.path
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Dict, List, Optional

import yaml

from backend import env
from backend.components import BKLogApi
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings

from .settings import grafana_settings
from .utils import os_env

logger = logging.getLogger(__name__)


@dataclass
class Datasource:
    """数据源标准格式"""

    uid: str
    name: str
    type: str
    url: str
    access: str = "direct"
    isDefault: bool = False
    withCredentials: bool = True
    database: Optional[Dict] = None
    jsonData: Optional[Dict] = None
    secureJsonData: Optional[Dict] = None

    version: int = 0


@dataclass
class Dashboard:
    """面板标准格式"""

    title: str
    dashboard: Dict
    folder: str = ""
    folderUid: str = ""
    overwrite: bool = True


class BaseProvisioning:
    def datasources(self, request, org_name: str, org_id: int) -> List[Datasource]:
        raise NotImplementedError(".datasources() must be overridden.")

    def dashboards(self, request, org_name: str, org_id: int) -> List[Dashboard]:
        raise NotImplementedError(".dashboards() must be overridden.")


class SimpleProvisioning(BaseProvisioning):
    """简单注入"""

    file_suffix = ["yaml", "yml"]

    def read_conf(self, name, suffix):
        if not grafana_settings.PROVISIONING_PATH:
            return []

        paths = os.path.join(grafana_settings.PROVISIONING_PATH, name, f"*.{suffix}")
        for path in glob.glob(paths):
            with open(path, "rb") as fh:
                conf = fh.read()
                expand_conf = os.path.expandvars(conf)
                ds = yaml.load(expand_conf, Loader=yaml.FullLoader)
                yield ds

    def datasources(self, request, org_name: str, org_id: int) -> List[Datasource]:
        """不注入数据源"""
        # 从db中获取监控token，并补充到环境变量
        bkm_dbm_token = SystemSettings.get_setting_value(key=SystemSettingsEnum.BKM_DBM_TOKEN.value)
        with os_env(ORG_NAME=org_name, ORG_ID=org_id, BKM_DBM_TOKEN=bkm_dbm_token):
            for suffix in self.file_suffix:
                for conf in self.read_conf("datasources", suffix):
                    for ds in conf["datasources"]:
                        yield Datasource(**ds)

    @staticmethod
    def replace_file_content(file_content: str, bkm_dbm_report: dict) -> str:
        """替换文件内容"""

        # 全局变量替换
        file_content = file_content.replace("{event_data_id}", str(bkm_dbm_report["event"]["data_id"]))
        file_content = file_content.replace("{metric_data_id}", str(bkm_dbm_report["metric"]["data_id"]))
        file_content = file_content.replace("{BK_SAAS_HOST}", env.BK_SAAS_HOST)

        # 刷新监控数据源ID：bkmonitor_timeseries
        file_content = file_content.replace("${DS_蓝鲸监控_- 指标数据}", "bkmonitor_timeseries")
        file_content = file_content.replace("${DS_日志平台}", "bklog")
        file_content = file_content.replace('"editable": true', '"editable": false')

        # 批量替换基础指标来源：system -> dbm_system
        file_content = file_content.replace("bkmonitor:system:", "bkmonitor:dbm_system:")
        file_content = file_content.replace('"result_table_id": "system.', '"result_table_id": "dbm_system.')
        return file_content

    @staticmethod
    def get_obj_datasource_type_uid(obj) -> tuple:
        datasource_type = obj.get("datasource", {}).get("type")
        if datasource_type == "bkmonitor-timeseries-datasource":
            uid = "bkmonitor_timeseries"
        elif datasource_type == "bk_log_datasource":
            uid = "bklog"
        else:
            uid = "unknown"
        return datasource_type, uid

    @classmethod
    def replace_dashboard(cls, dashboard: dict, used_index_name: list, index_name_id_map: dict):
        """
        调整仪表盘的一些参数
        """

        # 使用到日志数据源的，需要替换填充索引集ID
        for panel_index, panel in enumerate(dashboard["panels"]):
            # 递归处理所有 panel
            if "panels" in panel:
                dashboard["panels"][panel_index] = cls.replace_dashboard(panel, used_index_name, index_name_id_map)
            datasource_type, panel_uid = cls.get_obj_datasource_type_uid(panel)
            if datasource_type == "bkmonitor-timeseries-datasource":
                dashboard["panels"][panel_index]["datasource"]["uid"] = panel_uid
            if datasource_type == "bk_log_datasource":
                dashboard["panels"][panel_index]["datasource"]["uid"] = panel_uid
                for target_index, target in enumerate(panel["targets"]):
                    for label in target["data"]["index"].get("labels", []):
                        for index_name in used_index_name:
                            if index_name in label:
                                index_set_id = index_name_id_map.get(index_name, 0)
                                dashboard["panels"][panel_index]["targets"][target_index]["data"]["index"]["id"][
                                    1
                                ] = index_set_id
            # 处理 targets 的 datasource uid
            for target_index, target in enumerate(panel.get("targets", [])):
                datasource_type, target_uid = cls.get_obj_datasource_type_uid(target)
                if datasource_type:
                    dashboard["panels"][panel_index]["targets"][target_index]["datasource"]["uid"] = target_uid

        for tpl_index, tpl in enumerate(dashboard.get("templating", {}).get("list", [])):
            datasource_type, tpl_uid = cls.get_obj_datasource_type_uid(tpl)
            if datasource_type:
                dashboard["templating"]["list"][tpl_index]["datasource"]["uid"] = tpl_uid
            # 隐藏掉 app（业务）选择器
            if tpl["name"] == "app":
                dashboard["templating"]["list"][tpl_index]["hide"] = 2

        return dashboard

    def dashboards(self, request, org_name: str, org_id: int) -> List[Dashboard]:
        """固定目录下的json文件, 自动注入"""

        bkm_dbm_report = SystemSettings.get_setting_value(key=SystemSettingsEnum.BKM_DBM_REPORT.value)
        index_set = BKLogApi.search_index_set({"space_uid": f"bkcc__{env.DBA_APP_BK_BIZ_ID}"})
        index_name_id_map = {}
        # 在 grafana 中被使用的索引名
        used_index_name = [
            "mysql_slowlog",
            "mysql_db_table_size",
            "redis_slowlog",
            "redis_hotkey",
            "redis_bigkey",
            "redis_keymod",
        ]
        for index in index_set:
            for name in used_index_name:
                if name in index["index_set_name"]:
                    index_name_id_map[name] = index["index_set_id"]

        with os_env(ORG_NAME=org_name, ORG_ID=org_id):
            for suffix in self.file_suffix:
                for conf in self.read_conf("dashboards", suffix):
                    for p in conf["providers"]:
                        dashboard_path = os.path.expandvars(p["options"]["path"])
                        paths = os.path.join(dashboard_path, "*.json")
                        for path in glob.glob(paths):
                            with open(path, "rb") as fh:
                                file_content = fh.read().decode()
                                file_content = self.replace_file_content(file_content, bkm_dbm_report)

                                try:
                                    dashboard = json.loads(file_content)
                                except JSONDecodeError as err:
                                    logger.error(f"Failed to load {os.path.basename(path)}")
                                    raise err

                                dashboard["id"] = None
                                dashboard = self.replace_dashboard(dashboard, used_index_name, index_name_id_map)
                                title = dashboard.get("title")
                                if not title:
                                    continue
                                yield Dashboard(title=title, dashboard=dashboard)
