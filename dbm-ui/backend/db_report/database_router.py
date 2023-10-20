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
from django.db import models


class ReportRouter:
    route_app_labels = {"db_report"}

    def db_for_read(self, model: models.Model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return "report_db"
        return "default"

    def db_for_write(self, model: models.Model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return "report_db"
        return "default"

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            return db == "report_db"
        return db == "default"
