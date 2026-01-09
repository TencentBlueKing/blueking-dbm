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
from typing import List

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.models import Cluster
from backend.db_report.enums import TdbctlInstanceRole, TdbctlUpgradeStatus
from backend.db_report.models import TdbctlUpgradeRecord
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class TdbctlUpgradeStatusUpdateService(BaseService):
    """
    更新 tdbctl 实例的升级状态记录

    用于在流程执行过程中更新升级状态，而不是在流程构建阶段
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        self.log_info(_("传入参数:{}").format(kwargs))

        cluster_id = kwargs["cluster_id"]
        instances = kwargs["instances"]
        target_version = kwargs["target_version"]
        pkg_id = kwargs["pkg_id"]
        task_id = kwargs["task_id"]
        status = kwargs["status"]
        batch_id = kwargs.get("batch_id", "")
        operator = kwargs.get("operator", "system")
        error_msg = kwargs.get("error_msg", "")
        is_primary_list = kwargs.get("is_primary_list", [])
        current_versions = kwargs.get("current_versions", [])

        try:
            cluster = Cluster.objects.get(id=cluster_id)
        except Cluster.DoesNotExist:
            self.log_error(_("集群 {} 不存在").format(cluster_id))
            return False

        success = self._update_upgrade_status(
            cluster=cluster,
            instances=instances,
            target_version=target_version,
            pkg_id=pkg_id,
            task_id=task_id,
            status=status,
            batch_id=batch_id,
            operator=operator,
            error_msg=error_msg,
            is_primary_list=is_primary_list,
            current_versions=current_versions,
        )

        if success:
            self.log_info(_("成功更新 {} 个实例的升级状态为 {}").format(len(instances), status))
        else:
            self.log_warning(_("部分实例状态更新失败"))

        # 状态更新失败不应该阻塞流程执行，返回 True
        return True

    def _update_upgrade_status(
        self,
        cluster: Cluster,
        instances: List[dict],
        target_version: str,
        pkg_id: int,
        task_id: str,
        status: str,
        batch_id: str = "",
        operator: str = "system",
        error_msg: str = "",
        is_primary_list: List[bool] = None,
        current_versions: List[str] = None,
    ) -> bool:
        """
        更新 tdbctl 实例的升级状态

        @param cluster: 集群对象
        @param instances: tdbctl 实例列表
        @param target_version: 目标版本
        @param pkg_id: 升级包ID
        @param task_id: 关联的flow任务ID
        @param status: 升级状态
        @param batch_id: 批次ID
        @param operator: 操作人
        @param error_msg: 错误信息
        @param is_primary_list: 是否是 primary 的列表
        @param current_versions: 当前版本的列表
        @return: 是否全部成功
        """
        if not instances:
            return True

        all_success = True
        for idx, instance in enumerate(instances):
            ip = instance["ip"]
            port = instance["port"]
            spider_port = instance.get("spider_port", 0)

            # 确定实例角色
            is_primary = is_primary_list[idx] if is_primary_list and idx < len(is_primary_list) else False
            instance_role = TdbctlInstanceRole.PRIMARY.value if is_primary else TdbctlInstanceRole.SECONDARY.value

            # 获取当前版本
            current_version = current_versions[idx] if current_versions and idx < len(current_versions) else ""

            try:
                # 使用 update_or_create 更新或创建记录
                record, created = TdbctlUpgradeRecord.objects.update_or_create(
                    ip=ip,
                    port=port,
                    defaults={
                        "bk_biz_id": cluster.bk_biz_id,
                        "bk_cloud_id": cluster.bk_cloud_id,
                        "cluster_id": cluster.id,
                        "cluster_domain": cluster.immute_domain,
                        "spider_port": spider_port,
                        "instance_role": instance_role,
                        "current_version": current_version,
                        "target_version": target_version,
                        "status": status,
                        "task_id": task_id,
                        "pkg_id": pkg_id,
                        "batch_id": batch_id,
                        "error_msg": error_msg,
                        "updater": operator,
                    },
                )

                # 如果是新创建的记录，设置创建者
                if created:
                    record.creator = operator
                    record.upgrade_count = 1
                    record.save(update_fields=["creator", "upgrade_count"])
                else:
                    # 如果是更新记录，增加升级次数（仅当状态从非 RUNNING 变为 RUNNING 时）
                    if status == TdbctlUpgradeStatus.RUNNING.value:
                        record.upgrade_count = (record.upgrade_count or 0) + 1
                        record.save(update_fields=["upgrade_count"])

                # 追加历史记录
                record.append_history(
                    from_version=current_version,
                    to_version=target_version,
                    status=status,
                    task_id=task_id,
                    operator=operator,
                    error_msg=error_msg,
                )
                record.save(update_fields=["upgrade_history"])

                action = _("创建") if created else _("更新")
                self.log_info(_("{}升级记录: {}:{}, 状态={}").format(action, ip, port, status))

            except Exception as e:
                self.log_error(_("记录升级状态失败: {}:{}, 错误: {}").format(ip, port, str(e)))
                all_success = False

        return all_success


class TdbctlUpgradeStatusUpdateComponent(Component):
    name = __name__
    code = "tdbctl_upgrade_status_update"
    bound_service = TdbctlUpgradeStatusUpdateService
