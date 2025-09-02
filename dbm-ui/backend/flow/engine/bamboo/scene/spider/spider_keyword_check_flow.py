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
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, ProxyInstance
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.spider.upgrade_key_word_check import UpgradeKeyWordCheckComponent
from backend.flow.utils.mysql.mysql_act_dataclass import UpgradeKeyWordCheckKwargs
from backend.flow.utils.mysql.mysql_version_parse import spider_cross_major_version, tspider_version_parse

logger = logging.getLogger("flow")


class SpiderKeywordCheckFlow(object):
    """
    Spider关键字检查流程

    功能说明：
    1. 专门用于Spider集群的关键字检查
    2. 支持指定集群ID、业务ID和目标版本进行检查
    3. 只在跨主版本升级时进行检查
    4. 可配置检查类型和强制模式

    数据格式示例：
        {
            "bk_biz_id": 123,                    # 业务ID
            "cluster_id": 456,                   # 集群ID
            "target_version": "3.4.5",          # 目标版本
            "check_types": ["table_check", "column_check", "index_check"],  # 检查类型
            "force_check": False,                # 是否强制检查
            "uid": "admin",                      # 用户ID
            "created_by": "admin"                # 创建者
        }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        初始化SpiderKeywordCheckFlow

        参数说明：
        @param root_id: 任务流程定义的root_id，用于标识整个检查流程
        @param data: 单据传递参数，包含检查配置信息

        初始化流程：
        1. 设置基础流程参数
        2. 提取检查相关的配置参数
        3. 验证参数有效性
        """
        self.root_id = root_id
        self.data = data

        # 基础参数
        self.bk_biz_id = data["bk_biz_id"]
        self.cluster_id = data["cluster_id"]
        self.target_version = data["target_version"]
        self.uid = data["uid"]
        self.created_by = data["created_by"]

        # 检查配置参数
        self.check_types = data.get("check_types", ["table_check", "column_check", "index_check"])
        self.force_check = data.get("force_check", False)

        # 验证参数
        self._validate_params()

        # 获取集群信息
        self.cluster = self._get_cluster()

        logger.info(_("初始化Spider关键字检查流程: 集群ID={}, 目标版本={}").format(self.cluster_id, self.target_version))

    def _validate_params(self):
        """验证输入参数的有效性"""
        if not self.bk_biz_id:
            raise ValueError(_("业务ID不能为空"))

        if not self.cluster_id:
            raise ValueError(_("集群ID不能为空"))

        if not self.target_version:
            raise ValueError(_("目标版本不能为空"))

        if not self.check_types:
            raise ValueError(_("检查类型不能为空"))

    def _get_cluster(self) -> Cluster:
        """获取集群对象"""
        try:
            cluster = Cluster.objects.get(id=self.cluster_id, bk_biz_id=self.bk_biz_id)
            logger.info(_("获取集群信息成功: {}").format(cluster.name))
            return cluster
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(cluster_id=self.cluster_id, bk_biz_id=self.bk_biz_id, message=_("集群不存在"))

    def _get_spider_instances(self) -> list:
        """获取集群中的Spider实例"""
        spiders = ProxyInstance.objects.filter(cluster=self.cluster)
        if not spiders.exists():
            raise ValueError(_("集群中没有找到Spider实例"))

        logger.info(_("获取到 {} 个Spider实例").format(spiders.count()))
        return list(spiders)

    def run_keyword_check(self):
        """
        执行关键字检查流程的主入口方法

        执行流程：
        1. 获取集群中的Spider实例
        2. 检查是否跨主版本升级
        3. 如果是跨版本升级，执行关键字检查
        """
        logger.info(_("开始执行Spider关键字检查流程"))

        # 获取Spider实例
        spiders = self._get_spider_instances()

        # 构建检查流程
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 获取当前版本信息用于关键字检查
        from_version_map = {}

        # 检查是否跨版本升级
        is_cross_major_version = False
        for spider_ins in spiders:
            # 判断是否跨主版本
            if spider_cross_major_version(
                tspider_version_parse(self.target_version), tspider_version_parse(spider_ins.version)
            ):
                is_cross_major_version = True
                # 跨版本时，只需要存一个检查版本的实例
                # spider_ins.version 存的值 1.15
                if not from_version_map:
                    from_version_map[spider_ins.version] = [f"{spider_ins.machine.ip}:{spider_ins.port}"]

        if not is_cross_major_version:
            logger.info(_("非跨主版本升级，跳过关键字检查"))
            return

        # 添加关键字检查步骤
        pipeline.add_act(
            act_name=_("Spider关键字检查"),
            act_component_code=UpgradeKeyWordCheckComponent.code,
            kwargs=asdict(
                UpgradeKeyWordCheckKwargs(
                    cluster_id=self.cluster_id,
                    from_version_map=from_version_map,
                    to_version=self.target_version,
                    check_types=self.check_types,
                    schemas=None,  # 可以根据需要传入要检查的数据库列表
                    fail_on_conflict=not self.force_check,  # force_check为True时不因冲突失败
                )
            ),
        )

        logger.info(_("关键字检查流程构建完成，开始执行"))

        # 执行流程
        pipeline.run_pipeline()

        logger.info(_("Spider关键字检查流程执行完成"))

    def run(self):
        """流程执行入口"""
        self.run_keyword_check()
