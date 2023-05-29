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

from django.db.models import Q, QuerySet

from backend import env
from backend.components import CCApi

logger = logging.getLogger("root")


def in_another_cluster(instances: QuerySet) -> List[Dict]:
    return list(instances.filter(cluster__isnull=False))


def filter_out_instance_obj(instances: List[Dict], qs: QuerySet) -> QuerySet:
    queries = Q()
    for i in instances:
        queries |= Q(**{"machine__ip": i["ip"], "port": i["port"]})

    return qs.filter(queries)


def not_exists(instances: List[Dict], qs: QuerySet) -> List[Dict]:
    ne = set(map(lambda e: (e["ip"], e["port"]), instances)) - set(qs.values_list("machine__ip", "port"))
    return list(map(lambda e: {"ip": e[0], "port": e[1]}, ne))


def equ_list_of_dict(a, b: List) -> bool:
    d1 = [e for e in a if e not in b]
    d2 = [e for e in b if e not in a]
    logger.debug("{} {} {} {}".format(a, b, d1, d2))
    if d1 or d2:
        return False
    return True


def remain_instance_obj(instances: List[Dict], qs: QuerySet) -> List[Dict]:
    ne = set(qs.values_list("machine__ip", "port")) - set(map(lambda e: (e["ip"], e["port"]), instances))
    return list(map(lambda e: {"ip": e[0], "port": e[1]}, ne))


def add_service_instance(
    bk_module_id: int,
    bk_host_id: int,
    listen_ip: str,
    listen_port: int,
    func_name: str,
    labels_dict: dict = None,
    func_type: str = "custom",
) -> int:
    """
    定义添加bk-cc的服务实例的公共方法
    @param: bk_module_id: 模块idx
    @param: bk_host_id:   机器id
    @param: listen_ip:    进程监听ip
    @param: listen_port:  进程监听端口
    @param: func_name:    进程名称
    @param: labels_dict:  待加入的标签字典
    @param: func_type:    进程类型
    """

    # 添加服务实例信息，目前只操作一个，所以返回也是只有一个元素
    bk_instance_ids = list(
        CCApi.create_service_instance(
            {
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "bk_module_id": bk_module_id,
                "instances": [
                    {
                        "bk_host_id": bk_host_id,
                        "processes": [
                            {
                                "process_template_id": 0,
                                "process_info": {
                                    "bk_func_name": func_name,
                                    "bk_process_name": func_name,
                                    "bind_info": [
                                        {
                                            "enable": False,
                                            "ip": listen_ip,
                                            "port": str(listen_port),
                                            "protocol": "1",
                                            # "type": func_type,
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                ],
            }
        )
    )

    # 添加集群信息标签
    if labels_dict:
        CCApi.add_label_for_service_instance(
            {
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "instance_ids": bk_instance_ids,
                "labels": labels_dict,
            }
        )

    return bk_instance_ids[0]


def del_service_instance(bk_instance_id: int):
    # 这里因为id不存在会导致接口异常退出，这里暂时接收所有错误，不让它直接退出

    try:
        CCApi.delete_service_instance(
            {
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "service_instance_ids": [bk_instance_id],
            }
        )
    except Exception as error:
        logger.warning(error)
