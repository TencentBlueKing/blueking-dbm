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
from django.conf import settings
from django.utils.module_loading import import_string

# 默认配置
DEFAULTS = {
    "HOST": "http://127.0.0.1:3000",
    "PREFIX": "/",
    "ADMIN": ("admin", "admin"),
    "AUTHENTICATION_CLASSES": ["bk_dataview.grafana.authentication.SessionAuthentication"],
    "PERMISSION_CLASSES": ["bk_dataview.grafana.permissions.IsAuthenticated"],
    "PROVISIONING_CLASSES": ["bk_dataview.grafana.provisioning.SimpleProvisioning"],
    "PROVISIONING_PATH": "",
    "CODE_INJECTIONS": {
        "<head>": """<head>
            <style>
                .sidemenu {
                    display: none !important;
                }
                .navbar-page-btn .gicon-dashboard {
                    display: none !important;
                }
                .navbar .navbar-buttons--tv {
                    display: none !important;
                }
            </style>
        """
    },
    "BACKEND_CLASS": "bk_dataview.grafana.backends.api.APIHandler",
}

IMPORT_STRINGS = ["AUTHENTICATION_CLASSES", "PERMISSION_CLASSES", "PROVISIONING_CLASSES", "BACKEND_CLASS"]


APP_LABEL = "grafana"


class GrafanaSettings:
    def __init__(self, defaults=None, import_strings=None):
        self.user_settings = getattr(settings, "GRAFANA", {})
        self.defaults = defaults
        self.import_strings = import_strings

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError("Invalid Grafana setting: '%s'" % attr)

        try:
            # Check if present in user settings
            val = self.user_settings[attr]
        except KeyError:
            # Fall back to defaults
            val = self.defaults[attr]

        # Coerce import strings into classes
        if attr in self.import_strings:
            if isinstance(val, str):
                val = import_string(val)
            elif isinstance(val, (list, tuple)):
                val = [import_string(item) for item in val]
        return val


grafana_settings = GrafanaSettings(DEFAULTS, IMPORT_STRINGS)
