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


class SQLServerBinlogResult(models.Model):
    """SQLServer 事务日志备份结果，从 kafka 消费写入"""

    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    bk_biz_id = models.IntegerField()
    bk_cloud_id = models.IntegerField(default=0)
    cluster_id = models.IntegerField()
    # 不可变域名
    cluster_domain = models.CharField(max_length=255)
    db_role = models.CharField(max_length=32)
    host = models.CharField(max_length=32)
    port = models.IntegerField()
    backup_id = models.CharField(max_length=64)
    dbname = models.CharField(max_length=128)
    # 事务日志备份文件名
    file_name = models.CharField(max_length=256)
    file_cnt = models.IntegerField(default=1)
    # SQLServer 事务日志 LSN 字段
    first_lsn = models.CharField(max_length=30, default="")
    last_lsn = models.CharField(max_length=30, default="")
    checkpoint_lsn = models.CharField(max_length=30, default="")
    database_backup_lsn = models.CharField(max_length=30, default="")
    # 时间字段
    backup_task_start_time = models.DateTimeField(blank=True, null=True)
    backup_task_end_time = models.DateTimeField(blank=True, null=True)
    backup_begin_time = models.DateTimeField(blank=True, null=True)
    backup_end_time = models.DateTimeField(blank=True, null=True)
    backup_status = models.SmallIntegerField()
    backup_status_info = models.CharField(max_length=255)
    task_id = models.CharField(max_length=60)
    local_path = models.CharField(max_length=512)

    class Meta:
        db_table = "tb_sqlserver_binlog_result"
        indexes = [
            models.Index(
                fields=["cluster_id", "cluster_domain", "dbname", "backup_end_time"], name="idx_cluster_dbname_time"
            ),
        ]
        unique_together = [
            ("cluster_id", "cluster_domain", "host", "port", "backup_id", "dbname"),
        ]
