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


class TbTendisDTSJob(models.Model):
    id = models.BigAutoField(primary_key=True)
    bill_id = models.BigIntegerField(default=0, db_index=True, verbose_name=_("单据号"))
    app = models.CharField(max_length=64, default="", verbose_name=_("业务bk_biz_id"))
    bk_cloud_id = models.BigIntegerField(default=0, verbose_name=_("云区域id"))
    user = models.CharField(max_length=64, default="", verbose_name=_("申请人"))
    # DTS单据类型, 值包括
    # - cluster_nodes_num_update(集群节点数变更)
    # - cluster_type_update(集群类型变更)
    # - cluster_data_copy(集群数据复制)
    dts_bill_type = models.CharField(max_length=64, default="", verbose_name=_("DTS单据类型"))
    # DTS数据复制类型, 值包括
    # - one_app_diff_cluster(同一业务不同集群)
    # - diff_app_diff_cluster(不同业务不同集群)
    # - copy_from_rollback_temp(从回滚临时环境复制数据)
    # - copy_to_other_system(同步到其他系统,如迁移到腾讯云)
    # - user_built_to_dbm(业务自建迁移到dbm系统)
    dts_copy_type = models.CharField(max_length=64, default="", verbose_name=_("DTS数据复制类型"))
    # DTS 在线切换类型,值包括
    # - auto(自动切换)
    # - user_confirm(用户确认切换)
    online_switch_type = models.CharField(max_length=64, default="", verbose_name=_("在线切换类型"))
    datacheck = models.IntegerField(default=0, verbose_name=_("是否数据校验"))
    datarepair = models.IntegerField(default=0, verbose_name=_("是否数据修复"))
    # DTS 数据修复模式,值包括
    # - auto(自动修复)
    # - user_confirm(用户确认修复)
    datarepair_mode = models.CharField(max_length=64, default="", verbose_name=_("数据修复模式"))
    src_cluster = models.CharField(max_length=128, default="", verbose_name=_("源集群"))
    # 源集群类型,如 PredixyTendisplusCluster、TwemproxyTendisSSDInstance
    src_cluster_type = models.CharField(max_length=64, default="", verbose_name=_("源集群类型"))
    src_rollback_bill_id = models.BigIntegerField(default=0, verbose_name=_("回滚单据号"))
    src_rollback_instances = models.BinaryField(max_length=128, default=b"", verbose_name=_("回滚临时环境实例"))
    dst_bk_biz_id = models.CharField(max_length=64, default="", verbose_name=_("目标业务id"))
    dst_cluster = models.CharField(max_length=128, default="", verbose_name=_("目的集群"))
    # 目标集群类型,如 PredixyTendisplusCluster、TwemproxyTendisSSDInstance
    dst_cluster_type = models.CharField(max_length=64, default="", verbose_name=_("目标集群类型"))
    key_white_regex = models.BinaryField(default=b"", verbose_name=_("key正则(包含key)"))
    key_black_regex = models.BinaryField(default=b"", verbose_name=_("key正则(排除key)"))
    # 任务状态,该字段没用了
    status = models.IntegerField(default=0, db_index=True, verbose_name=_("任务状态"))
    reason = models.BinaryField(default=b"", verbose_name=_("bill备注"))
    create_time = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_("创建时间"))
    update_time = models.DateTimeField(auto_now=True, verbose_name=_("更新时间"))

    class Meta:
        db_table = "tb_tendis_dts_job"
        verbose_name = "tb_tendis_dts_job"
        verbose_name_plural = verbose_name
