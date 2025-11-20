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


class MysqlBackupProgress(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    event_create_timestamp = models.BigIntegerField(blank=True, null=True)
    event_report_timestamp = models.BigIntegerField(blank=True, null=True)
    event_receive_timestamp = models.BigIntegerField(blank=True, null=True)
    event_source_ip = models.CharField(max_length=30, blank=True, null=True)
    event_bk_cloud_id = models.BigIntegerField(blank=True, null=True)
    event_bk_biz_id = models.BigIntegerField(blank=True, null=True)
    backup_id = models.CharField(max_length=60)
    backup_type = models.CharField(max_length=32)
    cluster_id = models.BigIntegerField()
    cluster_domain = models.CharField(max_length=255)
    backup_host = models.CharField(max_length=32)
    backup_port = models.BigIntegerField()
    mysql_role = models.CharField(max_length=32)
    shard_value = models.BigIntegerField()
    bill_id = models.CharField(max_length=32)
    bk_biz_id = models.BigIntegerField()
    data_schema_grant = models.CharField(max_length=32)
    is_full_backup = models.IntegerField()
    status = models.CharField(max_length=32)
    status_detail = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "tb_mysql_backup_progress"
        app_label = "db_report"
