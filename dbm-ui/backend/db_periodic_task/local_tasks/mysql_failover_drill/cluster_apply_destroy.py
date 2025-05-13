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
import time
from typing import List

from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterStatus
from backend.db_meta.models import Cluster, LogicalCity
from backend.flow.consts import SUCCEED_STATES
from backend.flow.models import FlowTree

logger = logging.getLogger("celery")


def get_city_list() -> List:
    city_list = [city.name for city in LogicalCity.objects.all() if city.name != "default"]
    return city_list


def flow_status_polling(root_id: str, max_retry: int, interval: int) -> bool:
    """
    @param root_id: 根据root_id查询流程树状态
    @param max_retry: 最大重试次数
    @param interval: 重试间隔
    @return:
    """
    for n in range(max_retry):
        try:
            flow_tree = FlowTree.objects.get(root_id=root_id)
            logger.info(_("第 {}/{} 次轮询flow状态，当前状态为：{}".format(n, max_retry, flow_tree.status)))
            if flow_tree.status in SUCCEED_STATES:
                return True
            # 如果任务状态为failed，不返回，还是继续循环检查，在此期间可手动重试失败节点
            # elif flow_tree.status == TicketFlowStatus.FAILED:
            #     return False
        except FlowTree.DoesNotExist:
            logger.warning(_("retry {}/{}: FlowTree objects doesn't exist!".format(n, max_retry)))
        except Exception as e:
            logger.warning(_("retry {}/{}: Query exception!{}".format(n, max_retry, str(e))))

        if n < max_retry - 1:
            # 最后一次直接结束 避免继续等待
            time.sleep(interval * 60)

    return False


def cluster_status_polling(immute_domain: str, max_retry: int, interval: int):

    for n in range(max_retry):
        cluster = Cluster.objects.get(immute_domain=immute_domain)
        status = cluster.status
        logger.info(_("第 {}/{} 次轮询flow状态，当前集群状态为：{}".format(n, max_retry, status)))

        if status == ClusterStatus.ABNORMAL.value:
            return True

        if n < max_retry - 1:
            # 最后一次直接结束 避免继续等待
            time.sleep(interval * 60)

    return False
