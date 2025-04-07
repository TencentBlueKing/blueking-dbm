"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.utils.translation import ugettext_lazy as _

from backend.components import DRSApi
from backend.flow.engine.bamboo.scene.spider.common.exceptions import AddSpiderNodeFailedException


def get_flush_routing_sql_for_server(ctl_master: str, bk_cloud_id: int, add_spiders: list = None):
    """
    针对扩缩容单据的操作
    获取扩缩容spider节点的过程中，需要主动执行flush routing的server_name
    为什么要指定flush routing呢？因为在不停服扩容期间，在其余spider节点执行flush routing指令会有抖动的风险，严重会有hang住的可能。
    所以这里需要做精细化flush routing的行为
    目前版本有两种类型节点需要主动flush：ctl的slave节点；这次添加进去的spider节点
    可重试执行
    @param ctl_master: 当前集群的中控primary
    @param bk_cloud_id: 云区域id
    @param add_spiders: 加入list
    """
    # 对add_spiders参数做转空list处理，如果没有传
    if not add_spiders:
        add_spiders = []

    get_flush_routing_sql_list = []
    check_sql = "select Server_name, Host,Port,Wrapper from mysql.servers ;"
    res = DRSApi.rpc(
        {
            "addresses": [ctl_master],
            "cmds": ["set tc_admin=0", check_sql],
            "force": False,
            "bk_cloud_id": bk_cloud_id,
        }
    )
    if res[0]["error_msg"]:
        raise AddSpiderNodeFailedException(
            message=_("[_get_flush_routing_server_name]select mysql.servers failed: {}".format(res[0]["error_msg"]))
        )
    for i in res[0]["cmd_results"][1]["table_data"]:
        if i["Wrapper"] == "TDBCTL":
            # 中控slave节点加入
            get_flush_routing_sql_list.append(f"TDBCTL FLUSH SERVER {i['Server_name']} ROUTING;")

        elif i["Host"] in [s["ip"] for s in add_spiders]:
            # 本次加入的spider节点
            get_flush_routing_sql_list.append(f"TDBCTL FLUSH SERVER {i['Server_name']} ROUTING;")

    if not get_flush_routing_sql_list:
        # 需要flush routing不可能是空的，所以这里异常
        raise AddSpiderNodeFailedException(
            message=_("[_get_flush_routing_server_name]get_flush_routing_sql_list is null,check")
        )

    return get_flush_routing_sql_list
