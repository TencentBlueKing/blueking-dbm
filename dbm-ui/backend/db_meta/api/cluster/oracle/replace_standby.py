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

from backend.db_meta.api import machine, storage_instance
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Cluster, ClusterEntry, Machine, StorageInstance, StorageInstanceTuple

from . import change_password

logger = logging.getLogger("flow")


@transaction.atomic
def replace_standby(cluster_id: int, new_standby_ip: str, new_standby_port: int, bk_biz_id: int):
    """
    用新的 IP/Port 替换 Oracle 主备集群中的 Standby 节点。
    旧 standby 从集群中自动查询，新实例的规格、service_name、instance_inner_role 全部复用旧 standby。

    Args:
        cluster_id: 集群 ID
        new_standby_ip: 新 standby IP
        new_standby_port: 新 standby 端口
        bk_biz_id: 业务 ID
    """
    try:
        # ── 1. 找集群 & primary & 旧 standby ─────────────────────────────────
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        if cluster.cluster_type != ClusterType.OraclePrimaryStandby.value:
            raise ValueError(_("集群类型不是Oracle主备集群，是{}").format(cluster.cluster_type))
        bk_cloud_id = cluster.bk_cloud_id
        logger.info(_("找到集群: {}, 业务ID: {}, 云区域ID: {}").format(cluster.name, bk_biz_id, bk_cloud_id))

        primary_instance = cluster.storageinstance_set.get(instance_role=InstanceRole.PRIMARY.value)
        logger.info(_("找到Primary实例: {}:{}").format(primary_instance.machine.ip, primary_instance.port))

        old_standby = cluster.storageinstance_set.get(instance_role=InstanceRole.STANDBY.value)
        old_machine = old_standby.machine
        old_machine_cluster_type = old_machine.cluster_type
        logger.info(
            _("找到旧Standby实例: {}:{}, 机器ID: {}").format(old_standby.machine.ip, old_standby.port, old_machine.bk_host_id)
        )

        # ── 2. 创建新 Machine，复用旧机器规格 ────────────────────────────────
        # 先查询是否已存在对应机器
        new_machine = Machine.objects.filter(ip=new_standby_ip, bk_cloud_id=bk_cloud_id).first()

        # 如果不存在则创建新机器
        if not new_machine:
            machine.create(
                machines=[
                    {
                        "ip": new_standby_ip,
                        "bk_cloud_id": bk_cloud_id,
                        "bk_biz_id": bk_biz_id,
                        "machine_type": old_machine.machine_type,
                        "spec_id": old_machine.spec_id,
                        "spec_config": old_machine.spec_config,
                    }
                ],
                bk_cloud_id=bk_cloud_id,
            )

            new_machine = Machine.objects.filter(ip=new_standby_ip, bk_cloud_id=bk_cloud_id).first()
            # 为新机器设置 cluster_type
            new_machine.cluster_type = old_machine_cluster_type
            new_machine.save()

        logger.info(
            _("创建新机器: {}, 机器ID: {}, 规格ID: {}").format(new_standby_ip, new_machine.bk_host_id, old_machine.spec_id)
        )

        # ── 3. 创建新 StorageInstance，复用旧实例的 service_name 和 instance_inner_role ──
        # 先查询是否已存在对应实例
        new_standby = StorageInstance.objects.filter(
            machine=new_machine, port=new_standby_port, bk_biz_id=bk_biz_id
        ).first()

        # 如果不存在则创建新实例
        if not new_standby:
            storage_instance.create(
                instances=[
                    {
                        "ip": new_standby_ip,
                        "port": new_standby_port,
                        "instance_role": InstanceRole.STANDBY.value,
                        "name": old_standby.name,
                    }
                ]
            )
            new_standby = StorageInstance.objects.filter(
                machine=new_machine, port=new_standby_port, bk_biz_id=bk_biz_id
            ).first()
        logger.info(
            _("创建新Standby实例: {}:{}, 实例ID: {}, 角色: {}").format(
                new_standby_ip, new_standby_port, new_standby.id, InstanceRole.STANDBY.value
            )
        )

        # ── 4. 修改 StorageInstanceTuple ──────────────────────────────────────
        date = datetime.now()
        StorageInstanceTuple.objects.filter(
            ejector=primary_instance,
            receiver=old_standby,
        ).update(receiver=new_standby, update_at=date)
        logger.info(
            _("更新StorageInstanceTuple: 将Primary {}:{} 的接收者从旧Standby更新为新Standby").format(
                primary_instance.machine.ip, primary_instance.port
            )
        )

        # ── 5. 更新 ClusterEntry DNS 绑定 ─────────────────────────────────────
        slave_entries = ClusterEntry.objects.filter(
            cluster=cluster,
            cluster_entry_type=ClusterEntryType.DNS,
            role=ClusterEntryRole.SLAVE_ENTRY.value,
        )
        for entry in slave_entries:
            if entry.storageinstance_set.filter(id=old_standby.id).exists():
                entry.storageinstance_set.remove(old_standby)
                entry.storageinstance_set.add(new_standby)
                logger.info(_("更新ClusterEntry DNS绑定: 从旧Standby切换到新Standby, Entry: {}").format(entry.entry))

        # ── 6. 更新 Cluster.storageinstance_set ──────────────────────────────
        cluster.storageinstance_set.remove(old_standby)
        cluster.storageinstance_set.add(new_standby)
        cluster.save()
        logger.info(_("更新集群实例集合: 移除旧Standby, 添加新Standby"))

        # ── 7. 清理旧实例 & 旧机器 ────────────────────────────────────────────
        old_standby_ip = old_standby.machine.ip
        old_standby_port = old_standby.port
        old_standby.delete()
        logger.info(_("删除旧Standby实例: {}:{}").format(old_standby_ip, old_standby_port))

        if not StorageInstance.objects.filter(machine=old_machine).exists():
            old_machine.delete()
            logger.info(_("删除旧机器: {}").format(old_machine.ip))

        logger.info(
            _("Oracle standby替换完成，集群ID: {}, 新Standby: {}:{}").format(cluster_id, new_standby_ip, new_standby_port)
        )

        # ── 8. 密码修改 ────────────────────────────
        change_password.ip_change_password(
            old_standby_ip, old_standby_port, new_standby_ip, new_standby_port, bk_cloud_id
        )

    except Exception as e:
        logger.error(traceback.format_exc())
        raise Exception("oracle replace standby failed: {}".format(e))
