"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import gettext as _

from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.spider.validate.exception import SpiderCountFailedException
from backend.flow.engine.bamboo.scene.spider.validate.spider_switch_nodes_validate import (
    TenDBClusterSwitchNodesFlowValidator,
)
from backend.flow.engine.validate.base_validate import validator_log_format
from backend.flow.engine.validate.exceptions import DuplicateClusterException


class TenDBClusterNodesChangeSpecValidator(TenDBClusterSwitchNodesFlowValidator):
    """
    TenDBClusterNodesChangeSpecFlow类对应的validate类
    判断传入flow的data参数合法性
    校验内容：
    每行入参校验：
        检验1：传入集群合法性
        校验2：传入ip的合法性
        校验3：传入的spider角色的合法性
        校验4：传入的spider_ip必须全部传入
    聚合校验：
        检验1：同一个flow，不能传入重复集群
        检查4：传入替换节点过程中，在同一集群内，不能会超过集群spider节点部署上限
    """

    @validator_log_format
    def pre_check_is_including_all_spiders(self, info):
        """
        检查传入的spider ip列表是否包括所有
        @param info: 单据每行传入的参数
        """
        cluster = Cluster.objects.get(id=int(info["cluster_id"]))
        all_spiders = cluster.proxyinstance_set.filter(tendbclusterspiderext__spider_role=info["switch_spider_role"])
        spider_ip_set_from_info = set([i["ip"] for i in info["spider_old_ip_list"]])
        spider_ip_set_from_cluster = set([i.machine.ip for i in all_spiders])

        # 判断连个set是否完成对等，如果不对等则异常
        if spider_ip_set_from_cluster != spider_ip_set_from_info:
            return _("传入的spider列表，必须是集群的全部，请检查 \n")

        return ""

    def __run_check_for_info(self, info: dict, index: int) -> list:
        """
        @param info 单据每行传入的参数
        @param index 单据每行的编号
        """
        row_key = info.get("row_key", "")
        error_msg_list = []

        # 直接调用父类的方法
        error_msg_list.extend(super().run_check_for_info(info, index))

        # 增加校验：传入的spider_ip必须全部传入
        log_format_tag = self.create_log_tag(field="spider_old_ip_list", index=index, row_key=row_key)
        error_msg = self.pre_check_is_including_all_spiders(info, **log_format_tag)
        if error_msg:
            error_msg_list.append(error_msg)

        return error_msg_list

    def __call__(self):
        """
        发起校验, 实例函数化
        """

        # 阶段1 检测每个行的数据合法性
        error_msgs = []
        for index, info in enumerate(self.data["infos"]):
            error_msgs += self.__run_check_for_info(info, index)
        if error_msgs:
            return error_msgs

        # 阶段2 做聚合校验
        # 同一个flow，不能出现同样的集群ID
        err = self.pre_check_duplicate_cluster_ids("cluster_id")
        if err:
            raise DuplicateClusterException(err)

        # 传入替换节点过程中，在同一集群内，不能会超过集群spider节点部署上限
        err = self.pre_check_spider_upper_limit()
        if err:
            raise SpiderCountFailedException(err)

        return None
