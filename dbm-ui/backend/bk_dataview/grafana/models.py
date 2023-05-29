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

from .settings import APP_LABEL


class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    version = models.IntegerField()
    login = models.CharField(unique=True, max_length=190)
    email = models.CharField(unique=True, max_length=190)
    name = models.CharField(max_length=255, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    salt = models.CharField(max_length=50, blank=True, null=True)
    rands = models.CharField(max_length=50, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    org_id = models.BigIntegerField()
    is_admin = models.IntegerField()
    email_verified = models.IntegerField(blank=True, null=True)
    theme = models.CharField(max_length=255, blank=True, null=True)
    created = models.DateTimeField()
    updated = models.DateTimeField()
    help_flags1 = models.BigIntegerField()
    last_seen_at = models.DateTimeField(blank=True, null=True)
    is_disabled = models.IntegerField()

    class Meta:
        managed = False
        app_label = APP_LABEL
        db_table = "user"


class Org(models.Model):
    id = models.BigAutoField(primary_key=True)
    version = models.IntegerField()
    name = models.CharField(unique=True, max_length=190)
    address1 = models.CharField(max_length=255, blank=True, null=True)
    address2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    zip_code = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    billing_email = models.CharField(max_length=255, blank=True, null=True)
    created = models.DateTimeField()
    updated = models.DateTimeField()

    class Meta:
        managed = False
        app_label = APP_LABEL
        db_table = "org"


class OrgUser(models.Model):
    id = models.BigAutoField(primary_key=True)
    org_id = models.BigIntegerField()
    user_id = models.BigIntegerField()
    role = models.CharField(max_length=20)
    created = models.DateTimeField()
    updated = models.DateTimeField()

    class Meta:
        managed = False
        app_label = APP_LABEL
        db_table = "org_user"
        unique_together = (("org_id", "user_id"),)


class DataSource(models.Model):
    id = models.BigAutoField(primary_key=True)
    org_id = models.BigIntegerField()
    version = models.IntegerField()
    type = models.CharField(max_length=255)
    name = models.CharField(max_length=190)
    access = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    password = models.CharField(max_length=255, blank=True, null=True)
    user = models.CharField(max_length=255, blank=True, null=True)
    database = models.CharField(max_length=255, blank=True, null=True)
    basic_auth = models.BooleanField(default=False)
    basic_auth_user = models.CharField(max_length=255, blank=True, null=True)
    basic_auth_password = models.CharField(max_length=255, blank=True, null=True)
    is_default = models.BooleanField(default=False)
    json_data = models.TextField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=True)
    updated = models.DateTimeField(auto_now_add=True)
    with_credentials = models.BooleanField(default=False)
    secure_json_data = models.TextField(blank=True, null=True)
    read_only = models.BooleanField(default=False)

    def __str__(self):
        return f"<{self.id}, {self.name}>"

    class Meta:
        managed = False
        app_label = APP_LABEL
        db_table = "data_source"
        unique_together = (("org_id", "name"),)


class Dashboard(models.Model):
    id = models.BigAutoField(primary_key=True)
    version = models.IntegerField()
    slug = models.CharField(max_length=189)
    title = models.CharField(max_length=189)
    data = models.TextField()
    org_id = models.BigIntegerField()
    created = models.DateTimeField()
    updated = models.DateTimeField()
    updated_by = models.IntegerField(blank=True, null=True)
    created_by = models.IntegerField(blank=True, null=True)
    gnet_id = models.BigIntegerField(blank=True, null=True)
    plugin_id = models.CharField(max_length=189, blank=True, null=True)
    folder_id = models.BigIntegerField()
    is_folder = models.IntegerField()
    has_acl = models.IntegerField()
    uid = models.CharField(max_length=40, blank=True, null=True)

    class Meta:
        managed = False
        app_label = APP_LABEL
        db_table = "dashboard"
        unique_together = (
            ("org_id", "folder_id", "title"),
            ("org_id", "uid"),
        )
