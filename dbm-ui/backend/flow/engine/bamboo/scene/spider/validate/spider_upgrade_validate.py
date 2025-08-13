"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import ugettext as _

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, Machine
from backend.flow.engine.bamboo.scene.spider.validate.exception import SpiderRoleFailedException
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator


class TenDBClusterSpiderUpgradeValidator(MysqlBaseValidator):
    """
    TenDBClusterSpiderUpgrade类对应的validate类
    判断传入flow的data参数合法性

    校验内容：
    1. 检查待升级的spider机器的规格是否一致（包括spider_master和spider_slave），通过判断machine表里面的spec_config的spec_id
    2. 确保同一集群的所有spider节点具有相同的机器规格，避免因规格不一致导致的升级问题

    数据格式支持：
    - resource_spec格式：从集群中获取现有的spider master/slave IP列表
    - old_nodes格式：从old_nodes中获取spider master/slave IP列表

    错误处理：
    - 当发现规格不一致时，抛出SpiderRoleFailedException异常
    - 提供详细的错误信息，包含集群ID和具体的规格差异
    """

    def pre_check_spider_spec_consistency(self):
        """
        检查待升级的spider机器的规格是否一致（包括spider_master和spider_slave）
        通过检查machine表里面的spec_config的spec_id来判断

        校验逻辑：
        1. 遍历所有待升级的集群信息
        2. 获取每个集群的spider master和spider slave IP列表
        3. 查询这些IP对应的机器规格信息
        4. 分别检查spider_master和spider_slave内部的机器规格是否一致
        5. 如果发现规格不一致，记录错误信息

        支持的数据格式：
        - resource_spec格式：当resource_spec中包含spider_master/spider_slave时，从集群中获取现有IP
        - old_nodes格式：从old_nodes中获取spider_master/spider_slave IP列表

        返回：
        - list: 错误信息列表，如果没有错误则返回空列表
        """
        error_msgs = []

        # 遍历所有待升级的集群信息
        for index, info in enumerate(self.data["infos"]):
            cluster_id = info["cluster_id"]

            # 定义需要检查的spider角色和对应的中文名称
            spider_roles = {
                TenDBClusterSpiderRole.SPIDER_MASTER: "spider master",
                TenDBClusterSpiderRole.SPIDER_SLAVE: "spider slave",
            }

            # 检查每种spider角色的规格一致性
            for spider_role, role_name in spider_roles.items():
                spider_ips = []

                # 尝试从resource_spec中获取spider IP列表
                resource_spec = info.get("resource_spec", {})
                role_key = "spider_master" if spider_role == TenDBClusterSpiderRole.SPIDER_MASTER else "spider_slave"
                if role_key in resource_spec:
                    # 如果resource_spec中有对应角色，说明是资源池申请的情况
                    # 这种情况下需要从集群中获取现有的spider IP列表
                    try:
                        cluster = Cluster.objects.get(id=cluster_id)
                        spider_instances = cluster.proxyinstance_set.filter(
                            tendbclusterspiderext__spider_role=spider_role
                        )
                        spider_ips = [instance.machine.ip for instance in spider_instances]
                    except Exception:
                        # 如果获取集群信息失败，跳过这个集群的校验
                        continue
                else:
                    # 尝试从old_nodes中获取spider IP列表
                    old_nodes = info.get("old_nodes", {})
                    if isinstance(old_nodes, dict) and role_key in old_nodes:
                        # old_nodes是字典格式，包含对应角色键
                        spider_ips = old_nodes[role_key]
                    elif isinstance(old_nodes, list) and spider_role == TenDBClusterSpiderRole.SPIDER_MASTER:
                        # old_nodes是列表格式，直接作为spider_master IP列表使用（向后兼容）
                        spider_ips = old_nodes

                # 如果没有找到对应角色的IP列表，跳过当前角色的校验
                if not spider_ips:
                    continue

                # 查询这些IP对应的机器规格信息
                spec_ids = set()
                machines = Machine.objects.filter(ip__in=spider_ips)

                # 遍历所有机器，收集它们的规格ID
                for machine in machines:
                    spec_config = machine.spec_config or {}
                    # spec_config中的id字段就是spec_id，用于标识机器规格
                    spec_id = spec_config.get("id")
                    if spec_id:
                        spec_ids.add(spec_id)

                # 检查角色内部的规格一致性：如果发现多种不同的规格ID，说明规格不一致
                if len(spec_ids) > 1:
                    # 生成错误信息，包含集群ID、角色名称、规格数量和具体的规格ID列表
                    error_msg = _("集群 {} 的{}机器规格不一致，发现 {} 种不同规格: {}").format(
                        cluster_id, role_name, len(spec_ids), ", ".join(map(str, spec_ids))
                    )
                    error_msgs.append(error_msg)

        return error_msgs

    def __call__(self):
        """
        发起校验，实例函数化

        执行流程：
        1. 调用pre_check_spider_master_spec_consistency方法检查规格一致性
        2. 如果发现错误，抛出SpiderRoleFailedException异常
        3. 如果没有错误，返回None表示校验通过

        异常处理：
        - 当发现规格不一致时，抛出SpiderRoleFailedException
        - 异常消息包含所有发现的规格不一致问题

        返回：
        - None: 校验通过
        - 异常: 校验失败时抛出SpiderRoleFailedException
        """
        # 检查spider机器规格一致性（包括spider_master和spider_slave）
        error_msgs = self.pre_check_spider_spec_consistency()
        if error_msgs:
            # 将所有错误信息合并为一个字符串，并抛出异常
            raise SpiderRoleFailedException("\n".join(error_msgs))

        return None
