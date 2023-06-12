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
from django.utils.translation import ugettext_lazy as _

from backend.utils.time import datetime2str


class TbTendisDtsTask(models.Model):
    id = models.BigAutoField(primary_key=True)
    bill_id = models.BigIntegerField(verbose_name=_("单据号"))
    user = models.CharField(max_length=64, default="", verbose_name=_("申请人"))
    app = models.CharField(max_length=64, default="", verbose_name=_("业务bk_biz_id"))
    bk_cloud_id = models.BigIntegerField(default=0, verbose_name=_("云区域id"))
    dts_server = models.CharField(max_length=128, default="", verbose_name=_("执行迁移任务的dts_server"))
    src_cluster = models.CharField(max_length=128, default="", verbose_name=_("源集群"))
    src_cluster_priority = models.IntegerField(default=0, verbose_name=_("源集群优先级,值越大,优先级越高"))
    src_ip = models.CharField(max_length=128, default="", verbose_name=_("源slave_ip"))
    src_port = models.IntegerField(default=0, verbose_name=_("源slave_port"))
    src_password = models.CharField(max_length=128, default="", verbose_name=_("源实例密码base64值"))
    # 源slave db类型,如 tendis_ssd, tendis_cache,tendisplus
    src_dbtype = models.CharField(max_length=128, default="", verbose_name=_("源slave db类型"))
    # ssd=>rocksdbSize,tendisplus=>kvstore rocksdb size,cache=>used_memory
    src_dbsize = models.BigIntegerField(default=0, verbose_name=_("源实例数据量大小,单位Byte"))
    # twemproxy集群该segment_start、segment_end值才有效
    src_seg_start = models.IntegerField(default=0, verbose_name=_("源实例所属segment_start"))
    src_seg_end = models.IntegerField(default=0, verbose_name=_("源实例所属segment_end"))
    # 源实例权重,单个集群中根据实例的weight从小到大执行迁移
    src_weight = models.IntegerField(default=0, verbose_name=_("源实例权重"))
    # 在同一slave机器上执行太多迁移任务是危险的,所以需要控制
    src_ip_concurrency_limit = models.IntegerField(default=0, verbose_name=_("源slave_ip上task并发数控制"))
    src_ip_zonename = models.CharField(max_length=128, default="", verbose_name=_("源实例所在城市"))
    # tendisssd 相关 slave-keep-log-count参数
    src_old_logcount = models.BigIntegerField(default=0, verbose_name=_("源实例slave-keep-log-count的旧值"))
    src_new_logcount = models.BigIntegerField(default=0, verbose_name=_("源实例slave-keep-log-count的新值"))
    is_src_logcount_restored = models.IntegerField(default=0, verbose_name=_("源实例slave-keep-log-count是否恢复"))
    src_have_list_keys = models.IntegerField(default=0, verbose_name=_("srcRedis是否包含list类型key"))
    key_white_regex = models.BinaryField(default=b"", verbose_name=_("包含key(正则)"))
    key_black_regex = models.BinaryField(default=b"", verbose_name=_("排除key(正则)"))
    src_kvstore_id = models.IntegerField(default=0, verbose_name="tendisplus kvstore id")
    dst_cluster = models.CharField(max_length=128, default="", verbose_name=_("目的集群"))
    dst_password = models.CharField(max_length=128, default="", verbose_name=_("目的密码base64值"))
    # task类型,当前迁移任务到哪个阶段,包含tendis_backup, backupfile_fetch,tendisdump,sql_impoter,make_sync等
    task_type = models.CharField(max_length=128, default="", verbose_name=_("task类型"))
    tendisbackup_file = models.CharField(max_length=512, default="", verbose_name=_("tendisssd slave上bakup文件位置"))
    fetch_file = models.CharField(default="", max_length=512, verbose_name=_("backup文件拉取到dts_server本地位置"))
    sqlfile_dir = models.CharField(default="", max_length=512, verbose_name=_("tendisdumper得到的sql文件夹"))
    syncer_port = models.IntegerField(default=0, verbose_name=_("redis-sync端口"))
    syncer_pid = models.IntegerField(default=0, verbose_name=_("sync的进程id"))
    tendis_binlog_lag = models.BigIntegerField(default=0, verbose_name="redis-sync tendis_binlog_lag")
    retry_times = models.IntegerField(default=0, verbose_name=_("task重试次数"))
    # sync操作,包括: SyncStopTodo、ForceKillTaskTodo等
    sync_operate = models.CharField(default="", max_length=64, verbose_name=_("sync操作"))
    # 杀死syncer,0代表否,1代表是
    kill_syncer = models.IntegerField(default=0, verbose_name=_("杀死syncer"))
    # 任务执行状态,0:未开始 1:执行中 2:完成 -1:发生错误
    status = models.IntegerField(default=0, verbose_name=_("任务状态"))
    message = models.BinaryField(default=b"", verbose_name=_("信息"))
    # 迁移过程中被忽略的错误,如key同名不同类型WRONGTYPE Operation
    ignore_errlist = models.CharField(default="", max_length=512, verbose_name=_("被忽略的错误"))
    resync_from_time = models.DateTimeField(null=True, blank=True, verbose_name=_("sync从该时间点重新同步"))
    create_time = models.DateTimeField(auto_now_add=True, verbose_name=_("创建时间"))
    update_time = models.DateTimeField(auto_now=True, verbose_name=_("更新时间"))

    class Meta:
        db_table = "tb_tendis_dts_task"
        verbose_name = "Tendis Dts task"
        verbose_name_plural = "Tendis Dts task"
        indexes = [
            models.Index(fields=["update_time"], name="idx_update_time"),
            models.Index(fields=["dts_server", "update_time"], name="idx_jobserver_updatetime"),
            models.Index(fields=["bill_id", "src_cluster", "dst_cluster"], name="idx_billid_clusters"),
        ]

    def get_src_redis_addr(self) -> str:
        return "%s:%d" % (self.src_ip, self.src_port)


def dts_task_clean_passwd_and_format_time(json_data: dict, row: TbTendisDtsTask):
    json_data["src_password"] = ""
    json_data["dst_password"] = ""
    dts_task_format_time(json_data, row)


def dts_task_format_time(json_data: dict, row: TbTendisDtsTask):
    json_data["resync_from_time"] = datetime2str(row.resync_from_time) if row.resync_from_time else ""
    json_data["create_time"] = datetime2str(row.create_time)
    json_data["update_time"] = datetime2str(row.update_time)


def dts_task_binary_to_str(json_data: dict, row: TbTendisDtsTask):
    json_data["key_white_regex"] = row.key_white_regex.decode("utf-8") if row.key_white_regex else ""
    json_data["key_black_regex"] = row.key_black_regex.decode("utf-8") if row.key_black_regex else ""
    json_data["message"] = row.message.decode("utf-8") if row.message else ""
