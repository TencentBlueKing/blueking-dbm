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


class MysqlBackupResult(models.Model):
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
    cluster_address = models.CharField(max_length=255)
    backup_host = models.CharField(max_length=32)
    backup_port = models.BigIntegerField()
    mysql_role = models.CharField(max_length=32)
    shard_value = models.BigIntegerField()
    bill_id = models.CharField(max_length=32)
    bk_biz_id = models.BigIntegerField()
    mysql_version = models.CharField(max_length=120)
    data_schema_grant = models.CharField(max_length=32)
    is_full_backup = models.IntegerField()
    file_retention_tag = models.CharField(max_length=32)
    total_filesize = models.BigIntegerField()
    backup_consistent_time = models.DateTimeField(blank=True, null=True)
    backup_begin_time = models.DateTimeField()
    backup_end_time = models.DateTimeField()
    binlog_info = models.TextField()
    file_list = models.TextField()
    extra_fields = models.TextField()
    backup_status = models.CharField(max_length=32)
    backup_method = models.CharField(max_length=32, blank=True, null=True)
    is_standby = models.CharField(max_length=10)

    class Meta:
        managed = False
        db_table = "tb_mysql_backup_result"
        unique_together = (
            ("cluster_address", "shard_value", "mysql_role", "backup_id"),
            ("backup_host", "backup_port", "mysql_role", "backup_consistent_time"),
        )
