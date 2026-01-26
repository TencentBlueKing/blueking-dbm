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
from typing import Dict, List

from django.utils.translation import gettext as _

from backend.db_meta.models import Cluster
from backend.db_services.mysql.toolbox.tdbctl_upgrade_scheduler import TdbctlUpgradeScheduler
from backend.flow.engine.bamboo.scene.spider.upgrade.upgrade_tdbctl import (
    UpgradeTdbctlFlow,
    _filter_upgrade_instances,
    _get_tdbctl_instances,
)
from backend.ticket.constants import TicketType
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


class TdbctlUpgradeHandler:
    """
    TdbCtl 升级处理器

    封装 tdbctl 升级的核心业务逻辑，供 views 调用
    """

    def __init__(self, bk_biz_id: int, pkg_id: int, operator: str):
        """
        初始化处理器

        @param bk_biz_id: 业务ID
        @param pkg_id: 升级包ID
        @param operator: 操作人
        """
        self.bk_biz_id = bk_biz_id
        self.pkg_id = pkg_id
        self.operator = operator

        # 验证升级包并获取目标版本
        self.scheduler = TdbctlUpgradeScheduler(pkg_id=pkg_id, bk_biz_ids=[bk_biz_id])
        self.target_version = self.scheduler.target_version

    def filter_clusters_need_upgrade(self, clusters: List[Cluster]) -> Dict:
        """
        过滤出需要升级的集群（跳过版本已是最新的）

        @param clusters: 集群列表
        @return: 包含 upgraded_clusters 和 skipped_clusters 的字典
        """
        upgraded_clusters = []
        skipped_clusters = []

        for cluster in clusters:
            tdbctl_instances = _get_tdbctl_instances(cluster)
            if not tdbctl_instances:
                logger.warning(_("集群 {} 没有 tdbctl 实例，跳过").format(cluster.id))
                skipped_clusters.append(
                    {
                        "cluster_id": cluster.id,
                        "cluster_domain": cluster.immute_domain,
                        "reason": _("没有 tdbctl 实例"),
                    }
                )
                continue

            # 检查是否需要升级
            try:
                slave_instances, master_instances, version, skipped, skipped_versions = _filter_upgrade_instances(
                    tdbctl_instances, self.pkg_id, cluster.bk_cloud_id
                )
                # 如果所有实例都被跳过（版本已是最新），则跳过该集群
                if not slave_instances and not master_instances:
                    logger.info(_("集群 {} 的 tdbctl 版本已是最新，跳过").format(cluster.id))
                    skipped_clusters.append(
                        {
                            "cluster_id": cluster.id,
                            "cluster_domain": cluster.immute_domain,
                            "reason": _("版本已是最新"),
                        }
                    )
                else:
                    upgraded_clusters.append(cluster)
            except Exception as e:
                logger.error(_("检查集群 {} 版本时发生错误: {}").format(cluster.id, str(e)))
                skipped_clusters.append(
                    {
                        "cluster_id": cluster.id,
                        "cluster_domain": cluster.immute_domain,
                        "reason": _("版本检查失败: {}").format(str(e)),
                    }
                )

        return {
            "upgraded_clusters": upgraded_clusters,
            "skipped_clusters": skipped_clusters,
        }

    def execute_upgrade(self, clusters: List[Cluster]) -> str:
        """
        执行升级流程

        @param clusters: 需要升级的集群列表
        @return: flow 的 root_id
        """
        root_id = generate_root_id()
        infos = [{"cluster_id": c.id, "pkg_id": self.pkg_id} for c in clusters]

        flow_data = {
            "bk_biz_id": self.bk_biz_id,
            "bk_cloud_id": clusters[0].bk_cloud_id if clusters else 0,
            "uid": "",
            "created_by": self.operator,
            "ticket_type": TicketType.TENDBCLUSTER_TDBCTL_UPGRADE.value,
            "infos": infos,
        }

        logger.info(_("开始执行 tdbctl 升级流程: root_id={}, 集群数={}").format(root_id, len(clusters)))

        flow = UpgradeTdbctlFlow(root_id=root_id, data=flow_data)
        flow.run()

        logger.info(_("tdbctl 升级流程已启动: root_id={}").format(root_id))

        return root_id

    def upgrade(self, cluster_ids: List[int] = None, upgrade_all: bool = False) -> Dict:
        """
        执行 tdbctl 升级的主入口方法

        @param cluster_ids: 集群ID列表
        @param upgrade_all: 是否升级业务下所有 spider 集群
        @return: 升级结果
        """
        logger.info(
            _("同步执行 tdbctl 升级: bk_biz_id={}, cluster_ids={}, pkg_id={}, upgrade_all={}").format(
                self.bk_biz_id, cluster_ids, self.pkg_id, upgrade_all
            )
        )
        logger.info(_("目标升级版本: {}").format(self.target_version))

        # 1. 获取需要升级的集群列表
        clusters = self.get_clusters_to_upgrade(cluster_ids=cluster_ids, upgrade_all=upgrade_all)

        if not clusters:
            return {
                "result": True,
                "message": _("没有找到需要升级的 spider 集群"),
                "upgraded_clusters": [],
                "skipped_clusters": [],
            }

        # 2. 过滤出需要升级的集群
        filter_result = self.filter_clusters_need_upgrade(clusters)
        upgraded_clusters = filter_result["upgraded_clusters"]
        skipped_clusters = filter_result["skipped_clusters"]

        if not upgraded_clusters:
            return {
                "result": True,
                "message": _("所有集群版本已是最新，无需升级"),
                "upgraded_clusters": [],
                "skipped_clusters": skipped_clusters,
            }

        # 3. 执行升级
        root_id = self.execute_upgrade(upgraded_clusters)

        return {
            "result": True,
            "root_id": root_id,
            "message": _("升级任务已启动"),
            "upgraded_clusters": [c.id for c in upgraded_clusters],
            "skipped_clusters": skipped_clusters,
        }
