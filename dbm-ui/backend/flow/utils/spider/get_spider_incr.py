"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import copy
import logging

from django.utils.translation import ugettext_lazy as _

from backend.components import DRSApi
from backend.db_meta.models import Cluster
from backend.flow.consts import MAX_SPIDER_MASTER_COUNT
from backend.flow.engine.bamboo.scene.spider.common.exceptions import FailedToAssignIncrException

logger = logging.getLogger("root")


def get_spider_master_incr(cluster: Cluster, add_spiders: list) -> list:
    """
    根据待加入的spider-master/spider_mnt节点信息，计算出每个待加入节点的分片初始值
    每个spider节点每个分配到的值目前阶段必须小于等于37
    """
    new_add_spiders = copy.deepcopy(add_spiders)
    ctl_address = cluster.tendbcluster_ctl_primary_address()  # 随便拿一个spider-master接入层

    logger.info("ctl address: {}".format(ctl_address))
    res = DRSApi.rpc(
        {
            "addresses": [ctl_address],
            "cmds": ["set tc_admin=0", "select * from information_schema.TDBCTL_SPIDER_AUTO_INCREMENT"],
            "force": False,
            "bk_cloud_id": cluster.bk_cloud_id,
        }
    )

    print(res)

    if res[0]["error_msg"]:
        raise FailedToAssignIncrException(
            message=_("select spider_auto_increment failed: {}".format(res[0]["error_msg"]))
        )

    if not res[0]["cmd_results"][1]["table_data"]:
        raise FailedToAssignIncrException(message=_("select spider_auto_increment is null, check "))

    # 生成对比list
    tmp_list = [int(info["SPIDER_AUTO_INCREMENT_MODE_VALUE"]) for info in res[0]["cmd_results"][1]["table_data"]]

    # incr_number 从1开始寻找，如果已使用则跳过，直至到未使用则赋值给对应的待加入的spider-master节点，且跳出
    start = 0
    for spider in new_add_spiders:
        for incr_number in range(start + 1, MAX_SPIDER_MASTER_COUNT + 1):
            if incr_number not in tmp_list:
                spider["incr_number"] = incr_number
                break

        if not spider.get("incr_number"):
            # 如果没有分配到，则这里判断必定为空，证明这次添加spider-master已经大于到MAX_SPIDER_MASTER_COUNT预设值，需要退出
            raise FailedToAssignIncrException(
                message=_("The obtained incr is greater than MAX_SPIDER_MASTER_COUNT, check")
            )
        start = spider["incr_number"]

    return new_add_spiders
