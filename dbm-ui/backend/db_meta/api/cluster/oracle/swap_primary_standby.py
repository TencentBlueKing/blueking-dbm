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
import logging
import traceback
from datetime import datetime

from django.db import transaction
from django.utils.translation import gettext as _

from backend.db_meta.enums import InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstanceTuple

logger = logging.getLogger("flow")


@transaction.atomic
def swap_primary_standby(bk_biz_id: int, cluster_id: int):
    """
    通过集群 ID 自动查出 primary / standby 实例，执行角色互换
    操作内容：
    1. 互换两个实例的 instance_role
    2. 反转 StorageInstanceTuple 的 ejector / receiver
    3. 交换 ClusterEntry 绑定的实例（role 字段不变）
    Args:
    bk_biz_id: 业务 ID
    cluster_id: 集群 ID
    """

    try:
        # ── 1. 获取集群信息  ───────────────────────
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        if cluster.cluster_type != ClusterType.OraclePrimaryStandby.value:
            raise ValueError(_("集群类型不是Oracle主备集群，是{}").format(cluster.cluster_type))

        storage_objs = cluster.storageinstance_set.all()

        primary_inst = storage_objs.filter(instance_role=InstanceRole.PRIMARY.value).first()
        if not primary_inst:
            raise ValueError(_("集群 {} 未找到 PRIMARY 实例").format(cluster_id))
        standby_inst = storage_objs.filter(instance_role=InstanceRole.STANDBY.value).first()
        if not standby_inst:
            raise ValueError(_("集群 {} 未找到 STANDBY 实例").format(cluster_id))

        logger.info(
            _("[swap_primary_standby] 集群 {} 当前: primary={}:{} standby={}:{}").format(
                cluster_id,
                primary_inst.machine.ip,
                primary_inst.port,
                standby_inst.machine.ip,
                standby_inst.port,
            )
        )

        # ── 2. 互换实例 instance_role instance_inner_role───────────────────────
        old_primary_role = primary_inst.instance_role
        old_standby_role = standby_inst.instance_role
        old_primary_inner_role = primary_inst.instance_inner_role
        old_standby_inner_role = standby_inst.instance_inner_role

        primary_inst.instance_role = old_standby_role
        standby_inst.instance_role = old_primary_role
        primary_inst.instance_inner_role = old_standby_inner_role
        standby_inst.instance_inner_role = old_primary_inner_role

        date = datetime.now()
        primary_inst.update_at = date
        standby_inst.update_at = date

        primary_inst.save(update_fields=["instance_role", "instance_inner_role", "update_at"])
        standby_inst.save(update_fields=["instance_role", "instance_inner_role", "update_at"])
        logger.info(
            _("[swap_primary_standby] 实例角色已互换: instance_role {}: {} -> {}, instance_role {}: {} -> {}").format(
                primary_inst.machine.ip,
                primary_inst.port,
                primary_inst.instance_role,
                standby_inst.machine.ip,
                standby_inst.port,
                standby_inst.instance_role,
            )
        )
        logger.info(
            _(
                "[swap_primary_standby] 实例inner角色已互换: instance_inner_role {}: {} -> {}, instance_inner_role {}: {} -> {}"
            ).format(
                primary_inst.machine.ip,
                primary_inst.port,
                primary_inst.instance_inner_role,
                standby_inst.machine.ip,
                standby_inst.port,
                standby_inst.instance_inner_role,
            )
        )

        # ── 3. 反转 StorageInstanceTuple ────────────────────────────────────
        tuples = StorageInstanceTuple.objects.filter(
            ejector=primary_inst,
            receiver=standby_inst,
        )

        if not tuples.exists():
            raise ValueError(
                _("未找到 ejector={}:{} -> receiver={}:{} 的 tuple 记录").format(
                    primary_inst.machine.ip,
                    primary_inst.port,
                    standby_inst.machine.ip,
                    standby_inst.port,
                )
            )
        tuple_count = tuples.count()
        for t in tuples:
            t.ejector = standby_inst
            t.receiver = primary_inst
            t.update_at = date
            t.save(update_fields=["ejector", "receiver", "update_at"])
        logger.info(_("[swap_primary_standby] StorageInstanceTuple 已反转，共 {} 条").format(tuple_count))

        # ── 4. 交换 ClusterEntry 绑定的实例（role 不变）─────────────────────
        master_entry = ClusterEntry.objects.filter(
            cluster=cluster,
            storageinstance=primary_inst,
        ).first()

        slave_entry = ClusterEntry.objects.filter(
            cluster=cluster,
            storageinstance=standby_inst,
        ).first()

        if master_entry:
            master_entry.storageinstance_set.remove(primary_inst)
            master_entry.storageinstance_set.add(standby_inst)
            logger.info(
                _("[swap_primary_standby] entry {} 重新绑定到 {}:{}").format(
                    master_entry.entry,
                    standby_inst.machine.ip,
                    standby_inst.port,
                )
            )

        if slave_entry:
            slave_entry.storageinstance_set.remove(standby_inst)
            slave_entry.storageinstance_set.add(primary_inst)
            logger.info(
                _("[swap_primary_standby] entry {} 重新绑定到 {}:{}").format(
                    slave_entry.entry,
                    primary_inst.machine.ip,
                    primary_inst.port,
                )
            )

    except Exception as e:
        logger.error(traceback.format_exc())
        raise Exception(_("oracle primary/standby swap failed: {}").format(e)) from e
