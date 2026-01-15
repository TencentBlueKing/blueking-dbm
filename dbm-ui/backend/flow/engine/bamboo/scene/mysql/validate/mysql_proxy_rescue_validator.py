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
from backend.flow.engine.validate.exceptions import DuplicateIPException
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator

logger = logging.getLogger("flow")


class MySQLProxyRescueValidator(MysqlBaseValidator):
    """
    MySQL Proxy 救援流程校验类（多集群模式，偏尽快恢复）

    支持同时校验多个集群，每个集群对应 infos 列表中的一条记录。
    支持两种救援场景：
    1. 有旧 Proxy 元数据：所有原 Proxy 必须不可用
    2. 没有旧 Proxy 元数据：极端场景下仍可按参数继续救援（需补充 proxy_port 等）
    """

    # ------------------------------------------------------------------ #
    #  单行校验（接受 info 字典与行号，返回错误列表）
    # ------------------------------------------------------------------ #

    def __run_check_for_info(self, info: dict, index: int) -> list:
        """
        对单条 info 进行所有校验。

        @param info:  self.data["infos"] 中的单个元素
        @param index: 该元素的下标（用于错误日志标注）
        @return: 错误消息列表；空列表表示通过
        """
        row_key = info.get("row_key", "")

        # 校验1: 集群存在性
        log_tag = self.create_log_tag(field="cluster_id", index=index, row_key=row_key)
        error_msg = self.pre_check_cluster_exist([info["cluster_id"]], **log_tag)
        if error_msg:
            return [error_msg]

        # 校验2: Master 实例存在
        error_msg = self.__validate_master_available(info, index, row_key)
        if error_msg:
            return error_msg

        # 校验3: 参数完整性（无旧 Proxy 元数据时 proxy_port 必填）
        error_msg = self.__validate_parameters(info, index, row_key)
        if error_msg:
            return error_msg

        # 校验4: 所有原有 Proxy 必须不可用（核心安全校验）
        error_msg = self.__validate_all_proxies_unavailable(info, index, row_key)
        if error_msg:
            return error_msg

        # 校验5: 新机器未被 DBM 系统使用
        error_msg = self.__validate_new_machines_not_used(info, index, row_key)
        if error_msg:
            return error_msg

        return []

    # ------------------------------------------------------------------ #
    #  单行子校验方法
    # ------------------------------------------------------------------ #

    def __validate_all_proxies_unavailable(self, info: dict, index: int, row_key: str) -> list:
        """校验指定集群所有原有 Proxy 都不可用"""
        cluster_id = info["cluster_id"]
        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=self.data["bk_biz_id"])
        except Cluster.DoesNotExist:
            return []

        all_proxies = cluster.proxyinstance_set.all()

        if not all_proxies.exists():
            logger.warning(_("⚠️ 集群 {} 没有任何 Proxy 元数据记录，极端场景下按工单参数继续救援").format(cluster_id))
            return []

        # 元数据状态检查：所有 Proxy 的 status 必须是 UNAVAILABLE
        non_unavailable = all_proxies.exclude(status=InstanceStatus.UNAVAILABLE)
        if non_unavailable.exists():
            available_ips = [f"{p.machine.ip}:{p.port}(status={p.status})" for p in non_unavailable]
            return [
                _("infos[{}] 集群 {} 仍有非 UNAVAILABLE 状态的 Proxy 实例: {}，" "不允许执行救援流程。救援流程仅用于所有 Proxy 都故障的极端情况").format(
                    index, cluster_id, ", ".join(available_ips)
                )
            ]

        # DRS 实时连接检查：确认 Proxy 确实无法连接
        for proxy in all_proxies:
            if self.__check_proxy_available(proxy, cluster.bk_cloud_id):
                return [
                    _("infos[{}] 集群 {} 的 Proxy [{}:{}] 仍然可用（可连接），不允许执行救援流程").format(
                        index, cluster_id, proxy.machine.ip, proxy.admin_port
                    )
                ]

        logger.info(_("✅ infos[{}] 集群 {} 所有 Proxy 都处于 UNAVAILABLE 状态且确实不可连接").format(index, cluster_id))
        return []

    def __validate_parameters(self, info: dict, index: int, row_key: str) -> list:
        """参数完整性检查：无旧 Proxy 元数据时 proxy_port 为必填"""
        cluster_id = info["cluster_id"]
        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=self.data["bk_biz_id"])
        except Cluster.DoesNotExist:
            return []

        if not cluster.proxyinstance_set.exists():
            proxy_port = info.get("proxy_port")
            if not proxy_port:
                return [_("infos[{}] 集群 {} 没有旧 Proxy 元数据，必须在工单参数中提供 proxy_port").format(index, cluster_id)]
            logger.info(_("✅ infos[{}] 集群 {} 使用用户提供的端口: {}").format(index, cluster_id, proxy_port))

        return []

    def __validate_master_available(self, info: dict, index: int, row_key: str) -> list:
        """校验指定集群 Master 实例存在"""
        cluster_id = info["cluster_id"]
        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=self.data["bk_biz_id"])
        except Cluster.DoesNotExist:
            return []

        master = cluster.storageinstance_set.filter(instance_role=InstanceRole.BACKEND_MASTER).first()
        if not master:
            return [_("infos[{}] 集群 {} 没有 Master 实例").format(index, cluster_id)]

        return []

    def __validate_new_machines_not_used(self, info: dict, index: int, row_key: str) -> list:
        """校验该 info 中的新机器未被 DBM 系统使用"""
        for new_proxy in info.get("new_proxies", []):
            existing = Machine.objects.filter(ip=new_proxy["ip"], bk_cloud_id=new_proxy["bk_cloud_id"]).first()
            if existing:
                return [_("infos[{}] 机器 {} 已在 DBM 系统中，不能用于救援").format(index, new_proxy["ip"])]
        return []

    # ------------------------------------------------------------------ #
    #  辅助工具
    # ------------------------------------------------------------------ #

    def __check_proxy_available(self, proxy, bk_cloud_id) -> bool:
        """检查 Proxy 是否可用（通过 DRS 验证），可连接返回 True"""
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
            return not res[0].get("error_msg")
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    #  入口
    # ------------------------------------------------------------------ #

    def __call__(self):
        """执行所有校验（多集群模式）"""
        infos = self.data.get("infos", [])

        # 阶段1：逐行校验
        error_msgs = []
        for index, info in enumerate(infos):
            error_msgs += self.__run_check_for_info(info, index)
        if error_msgs:
            return error_msgs

        # 阶段2：聚合校验 — 所有 infos 的 new_proxies IP 不能跨集群重复
        err = self.pre_check_duplicate_ip("new_proxies")
        if err:
            raise DuplicateIPException(err)

        return None
