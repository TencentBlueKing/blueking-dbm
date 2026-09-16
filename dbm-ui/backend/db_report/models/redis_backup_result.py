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


class RedisBackupResult(models.Model):
    """Unmanaged mapping of tb_redis_backup_result (report_db)."""

    id = models.BigAutoField(primary_key=True)
    backup_type = models.CharField(max_length=32)
    immute_domain = models.CharField(max_length=255)
    backup_host = models.CharField(max_length=32)
    backup_port = models.IntegerField()
    redis_role = models.CharField(max_length=32)
    redis_type = models.CharField(max_length=32)
    bk_biz_id = models.BigIntegerField()
    backup_taskid = models.CharField(max_length=128)
    backup_file_size = models.BigIntegerField()
    backup_file = models.CharField(max_length=255)
    shard_value = models.CharField(max_length=255, blank=True, null=True)
    backup_tag = models.CharField(max_length=255)
    backup_identify = models.CharField(max_length=255)
    is_standby = models.CharField(max_length=10, blank=True, null=True)
    backup_begin_time = models.DateTimeField(blank=True, null=True)
    backup_end_time = models.DateTimeField(blank=True, null=True)
    extra_fields = models.TextField()
    backup_status = models.CharField(max_length=32)

    class Meta:
        managed = False
        db_table = "tb_redis_backup_result"
        app_label = "db_report"


class RedisBinlogResult(models.Model):
    """Unmanaged mapping of tb_redis_binlog_result (report_db). Phase 1 unused."""

    id = models.BigAutoField(primary_key=True)
    backup_type = models.CharField(max_length=32)
    immute_domain = models.CharField(max_length=255)
    backup_host = models.CharField(max_length=32)
    backup_port = models.IntegerField()
    kvstoreidx = models.IntegerField()
    redis_role = models.CharField(max_length=32)
    redis_type = models.CharField(max_length=32)
    bk_biz_id = models.BigIntegerField()
    backup_taskid = models.CharField(max_length=128)
    backup_file_size = models.BigIntegerField()
    backup_file = models.CharField(max_length=255)
    shard_value = models.CharField(max_length=255, blank=True, null=True)
    backup_tag = models.CharField(max_length=255)
    backup_begin_time = models.DateTimeField(blank=True, null=True)
    backup_end_time = models.DateTimeField(blank=True, null=True)
    backup_status = models.CharField(max_length=32)

    class Meta:
        managed = False
        db_table = "tb_redis_binlog_result"
        app_label = "db_report"
