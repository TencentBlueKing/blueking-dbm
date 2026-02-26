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


class MysqlPartitionResult(models.Model):
    """
    映射 bk_dbm_report 库中的 tb_mysql_partition_result 表。

    表由外部系统管理，Django 只做只读/写入 ORM 映射，因此 managed=False。
    """

    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    event_create_timestamp = models.BigIntegerField(blank=True, null=True)
    event_report_timestamp = models.BigIntegerField(blank=True, null=True)
    event_receive_timestamp = models.BigIntegerField(blank=True, null=True)
    event_source_ip = models.CharField(max_length=30, blank=True, null=True)
    event_bk_cloud_id = models.BigIntegerField(blank=True, null=True)
    event_bk_biz_id = models.BigIntegerField(blank=True, null=True)
    event_uuid = models.CharField(max_length=60, blank=True, null=True)

    bk_cloud_id = models.BigIntegerField()
    bk_biz_id = models.BigIntegerField()
    cluster_type = models.CharField(max_length=32)
    config_id = models.BigIntegerField()

    # MySQL 中为 TIMESTAMP，交由数据库填充默认值，这里不设置 auto_now/auto_now_add
    create_time = models.DateTimeField()

    status = models.CharField(max_length=32)
    exec_log = models.TextField()

    class Meta:
        managed = False
        db_table = "tb_mysql_partition_result"
