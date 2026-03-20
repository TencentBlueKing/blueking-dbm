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


class SQLServerBackupResult(models.Model):
    """SQLServer 全量备份结果"""

    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    backup_id = models.CharField(max_length=60)
    backup_type = models.CharField(max_length=32)
    cluster_id = models.IntegerField()
    cluster_domain = models.CharField(max_length=255)
    backup_host = models.CharField(max_length=32)
    backup_port = models.IntegerField()
    master_ip = models.CharField(max_length=32, default="")
    master_port = models.IntegerField(default=0)
    role = models.CharField(max_length=32, default="")
    bill_id = models.CharField(max_length=32, default="")
    bk_biz_id = models.IntegerField()
    bk_cloud_id = models.IntegerField(default=0)
    charset = models.CharField(max_length=64, default="")
    time_zone = models.CharField(max_length=16, default="+08:00")
    version = models.CharField(max_length=64, default="")
    data_schema_grant = models.CharField(max_length=32, default="")
    # 是否为包含数据的全量备份
    is_full_backup = models.BooleanField()
    # LSN 字段 - 使用字符串存储，因为 SQLServer LSN 可能超出 int64 最大值
    first_lsn = models.CharField(max_length=30, default="")
    last_lsn = models.CharField(max_length=30, default="")
    checkpoint_lsn = models.CharField(max_length=30, default="")
    database_backup_lsn = models.CharField(max_length=30, default="")
    # 时间字段
    backup_task_start_time = models.DateTimeField(blank=True, null=True)
    backup_task_end_time = models.DateTimeField(blank=True, null=True)
    backup_begin_time = models.DateTimeField(blank=True, null=True)
    backup_end_time = models.DateTimeField(blank=True, null=True)
    # 其他字段
    db_list = models.TextField()
    dbname = models.CharField(max_length=128, default="")
    file_cnt = models.IntegerField(default=0)
    task_id = models.CharField(max_length=64, default="")
    file_name = models.CharField(max_length=255, default="")
    file_size_kb = models.BigIntegerField(default=0)
    db_size_kb = models.BigIntegerField(default=0)
    compatibility_level = models.IntegerField(default=0)
    local_path = models.CharField(max_length=255, default="")

    class Meta:
        db_table = "tb_sqlserver_dbbackup_result"
        indexes = [
            models.Index(fields=["cluster_id", "cluster_domain", "backup_end_time"], name="idx_cluster_time"),
        ]
        unique_together = [
            ("cluster_id", "cluster_domain", "backup_host", "backup_port", "backup_id", "dbname"),
        ]
