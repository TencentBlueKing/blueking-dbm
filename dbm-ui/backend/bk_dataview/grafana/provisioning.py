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
from typing import Dict, List, Optional

import yaml

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
                ds = yaml.load(expand_conf)
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

    def dashboards(self, request, org_name: str, org_id: int) -> List[Dashboard]:
        """固定目录下的json文件, 自动注入"""
        with os_env(ORG_NAME=org_name, ORG_ID=org_id):
            for suffix in self.file_suffix:
                for conf in self.read_conf("dashboards", suffix):
                    for p in conf["providers"]:
                        dashboard_path = os.path.expandvars(p["options"]["path"])
                        paths = os.path.join(dashboard_path, f"*.json")
                        for path in glob.glob(paths):
                            with open(path, "rb") as fh:
                                dashboard = json.loads(fh.read())
                                title = dashboard.get("title")
                                if not title:
                                    continue
                                yield Dashboard(title=title, dashboard=dashboard)
