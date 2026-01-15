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

from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.db_meta.enums import InstanceRole, InstanceStatus
from backend.db_meta.models import Cluster, Machine
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator

logger = logging.getLogger("flow")


class MySQLProxyRescueValidator(MysqlBaseValidator):
    """
    MySQL Proxy 救援流程校验类（偏尽快恢复，不做旧 Proxy 版本一致性等耗时/易阻塞校验）

    支持两种救援场景：
    1. 有旧 Proxy 元数据：所有原 Proxy 必须不可用
    2. 没有旧 Proxy 元数据：极端场景下仍可按参数继续救援（需补充 proxy_port 等）
    """

    def validate_all_proxies_unavailable(self):
        """
        校验所有原有 Proxy 都不可用

        ⚠️ 关键改进: 如果没有旧 Proxy 元数据，不阻止救援流程

        核心安全检查：
        1. 如果有 Proxy 元数据：status 必须是 UNAVAILABLE + DRS 验证
        2. 如果没有 Proxy 元数据：跳过此检查
        """
        cluster_id = self.data.get("cluster_id")
        if not cluster_id:
            return [_("参数错误: 缺少 cluster_id")]

        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=self.data["bk_biz_id"])
        except Cluster.DoesNotExist:
            return [_("集群 {} 不存在").format(cluster_id)]

        all_proxies = cluster.proxyinstance_set.all()

        # ✅ 改进：如果没有旧 Proxy 元数据，允许继续（极端场景）
        if not all_proxies.exists():
            logger.warning(_("⚠️ 集群 {} 没有任何 Proxy 元数据记录，极端场景下按工单参数继续救援").format(cluster_id))
            return None  # 允许继续，不阻止救援

        # 校验1: 元数据状态检查 - 所有 Proxy 的 status 必须是 UNAVAILABLE
        non_unavailable_proxies = all_proxies.exclude(status=InstanceStatus.UNAVAILABLE)

        if non_unavailable_proxies.exists():
            available_ips = [f"{p.machine.ip}:{p.port}(status={p.status})" for p in non_unavailable_proxies]
            return [
                _("集群仍有非 UNAVAILABLE 状态的 Proxy 实例: {}，不允许执行救援流程。" "救援流程仅用于所有 Proxy 都故障的极端情况").format(
                    ", ".join(available_ips)
                )
            ]

        # 校验2: DRS 实时连接检查 - 确认 Proxy 确实无法连接
        for proxy in all_proxies:
            if self._check_proxy_available(proxy, cluster.bk_cloud_id):
                return [_("Proxy [{}:{}] 仍然可用（可连接），不允许执行救援流程").format(proxy.machine.ip, proxy.admin_port)]

        logger.info(_("✅ 校验通过: 集群 {} 所有 Proxy 都处于 UNAVAILABLE 状态且确实不可连接").format(cluster_id))
        return None

    def validate_parameters(self):
        """
        ✅ 新增校验: 参数完整性检查

        如果没有旧 Proxy 元数据，则 proxy_port 参数为必填
        """
        cluster_id = self.data.get("cluster_id")
        if not cluster_id:
            return None

        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=self.data["bk_biz_id"])
        except Cluster.DoesNotExist:
            return None

        all_proxies = cluster.proxyinstance_set.all()

        # 如果没有旧 Proxy 元数据，proxy_port 必填
        if not all_proxies.exists():
            proxy_port = self.data.get("proxy_port")
            if not proxy_port:
                return [_("集群没有旧 Proxy 元数据，必须在工单参数中提供 proxy_port")]
            logger.info(_("✅ 使用用户提供的端口: {}").format(proxy_port))

        return None

    def _check_proxy_available(self, proxy, bk_cloud_id):
        """检查 Proxy 是否可用（通过 DRS 验证）"""
        try:
            proxy_admin_instance = f"{proxy.machine.ip}:{proxy.admin_port}"
            res = DRSApi.proxyrpc(
                {
                    "addresses": [proxy_admin_instance],
                    "cmds": ["select version;"],
                    "force": False,
                    "bk_cloud_id": bk_cloud_id,
                }
            )
            # 如果没有错误信息，说明 Proxy 可用
            return not res[0].get("error_msg")
        except Exception:
            # 连接失败，Proxy 不可用
            return False

    def validate_master_available(self):
        """校验 Master 实例可用"""
        cluster_id = self.data.get("cluster_id")
        if not cluster_id:
            return None

        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=self.data["bk_biz_id"])
        except Cluster.DoesNotExist:
            return None

        master = cluster.storageinstance_set.filter(instance_role=InstanceRole.BACKEND_MASTER).first()

        if not master:
            return [_("集群没有 Master 实例")]

        return None

    def validate_new_machines_not_used(self):
        """校验新机器未被 DBM 系统使用"""
        new_proxies = self.data.get("new_proxies", [])

        for new_proxy in new_proxies:
            existing_machine = Machine.objects.filter(ip=new_proxy["ip"], bk_cloud_id=new_proxy["bk_cloud_id"]).first()

            if existing_machine:
                return [_("机器 {} 已在 DBM 系统中，不能用于救援").format(new_proxy["ip"])]

        return None

    def __call__(self):
        """执行所有校验"""
        # 校验1: 集群存在性
        cluster_id = self.data.get("cluster_id")
        if cluster_id:
            error_msg = self.pre_check_cluster_exist([cluster_id])
            if error_msg:
                return [error_msg]

        # 校验2: Master 可用性
        error_msg = self.validate_master_available()
        if error_msg:
            return error_msg

        # 校验3: ✅ 新增 - 参数完整性检查
        error_msg = self.validate_parameters()
        if error_msg:
            return error_msg

        # 校验4: ⚠️ 核心校验 - 所有原有 Proxy 必须不可用（已优化）
        error_msg = self.validate_all_proxies_unavailable()
        if error_msg:
            return error_msg

        # 校验5: 新机器未被使用
        error_msg = self.validate_new_machines_not_used()
        if error_msg:
            return error_msg

        return None
