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
from pipeline.component_framework.component import Component

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.mysql.sync_master import SyncMasterService

logger = logging.getLogger("flow")


class SyncCtlMasterService(SyncMasterService):
    """
    Spider 中控 (tdbctl) 集群"建立主从同步"专用活动节点。

    设计动机:
        SyncMasterService 父类负责"对给定 master 实例创建 repl 账号 -> 在 slaves 上
        CHANGE MASTER TO 建立同步"。在 spider 扩容子流程里, 上层编排会先在 dbm-ui 进程
        中调用 cluster.tendbcluster_ctl_primary_address() 拿到当时的 ctl primary, 再把
        它作为 kwargs["master"] 缓存进 pipeline payload。

        但是从编排到该活动节点真正执行之间, 集群可能因为运维操作 (如手动 TDBCTL ENABLE
        PRIMARY、上一步活动节点中触发的中控切换等) 发生 ctl primary 漂移; 此时如果仍
        把缓存的 ip 当作 master 去 CHANGE MASTER TO, 新加入的中控就会指向一个非 primary
        的节点, 后续 flush routing / tdbctl create node 都会失败。

    本 Service 在 _execute 入口做"运行时再校准":
        1. 通过 kwargs["cluster_id"] 取 Cluster, 调 tendbcluster_ctl_primary_address()
           拿到运行时最新 primary;
        2. 与上层缓存的 kwargs["master"] (host:port) 对比;
        3. 若不一致:
              a) 把 kwargs["master"] 改写为最新 primary;
              b) 若最新 primary 此时正出现在 kwargs["slaves"] 列表里 (例如上一轮被当作
                 待加入 slave), 则将其从 slaves 中剔除, 避免 "自己 CHANGE MASTER TO
                 自己" 的非法拓扑;
        4. 调用 super()._execute(data, parent_data) 走父类原有同步建立链路。

    使用约定 (kwargs 必填):
        cluster_id:        集群 id, 用于实时探测 ctl primary, 必填。
        bk_biz_id / bk_cloud_id / priv_role / master / slaves / is_gtid /
        is_add_any / is_master_add_priv: 含义与 MysqlSyncMasterKwargs 一致。

    备注:
        - kwargs["master"] / kwargs["slaves"] 在执行期是 dict 形式 (dataclass.asdict
          展开后传入 pipeline), 故按 dict 处理。
        - port 字段类型遵循上层调用约定 (str 或 int), 本 Service 不做强制转换, 仅按字
          符串拼接对比 host:port。
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        cluster_id = kwargs.get("cluster_id")
        if not cluster_id:
            self.log_error(_("kwargs 缺少 cluster_id, 无法探测最新 ctl primary"))
            return False

        cluster = Cluster.objects.get(id=cluster_id)

        master = kwargs.get("master") or {}
        cached_host = master.get("host")
        cached_port = master.get("port")
        cached_master = f"{cached_host}{IP_PORT_DIVIDER}{cached_port}"

        # 运行时实时探测最新 ctl primary
        latest_master = cluster.tendbcluster_ctl_primary_address()
        latest_host, latest_port_str = latest_master.split(IP_PORT_DIVIDER)

        self.log_info(
            _("[{}] 上层缓存的 ctl primary 为: {}, 实时探测的 ctl primary 为: {}").format(
                cluster.immute_domain, cached_master, latest_master
            )
        )

        if cached_master != latest_master:
            self.log_warning(
                _("[{}] ctl primary 已发生漂移, 改用最新 primary 建立同步: {} -> {}").format(
                    cluster.immute_domain, cached_master, latest_master
                )
            )

            # 与缓存 master 端口类型保持一致 (str/int), 避免下游字符串拼接错位。
            if isinstance(cached_port, int):
                latest_port = int(latest_port_str)
            else:
                latest_port = latest_port_str

            # 改写 master
            kwargs["master"] = {"host": latest_host, "port": latest_port}

            # 若 slaves 中包含最新 primary, 则剔除, 避免 "自己 CHANGE MASTER TO 自己"
            slaves = kwargs.get("slaves") or []
            new_slaves = [s for s in slaves if s.get("host") != latest_host]
            if len(new_slaves) != len(slaves):
                self.log_warning(
                    _("[{}] 最新 primary [{}] 出现在 slaves 列表中, 已自动剔除").format(cluster.immute_domain, latest_host)
                )
            kwargs["slaves"] = new_slaves

            # 写回 data, 兼容部分 pipeline 实现下 get_one_of_inputs 返回的不是同一引用
            data.get_one_of_inputs("kwargs")["master"] = kwargs["master"]
            data.get_one_of_inputs("kwargs")["slaves"] = kwargs["slaves"]

            if not new_slaves:
                self.log_warning(_("[{}] 漂移剔除后 slaves 为空, 无需建立同步, 直接跳过本活动节点").format(cluster.immute_domain))
                return True
        else:
            self.log_info(_("[{}] ctl primary 未发生漂移, 沿用上层编排时的 master").format(cluster.immute_domain))

        # 走父类原有 SyncMaster 同步建立链路
        return super()._execute(data, parent_data)


class SyncCtlMasterComponent(Component):
    """
    Pipeline 组件注册类: 将 SyncCtlMasterService 注册为可在流程编排中使用的组件,
    用于在执行 Spider 中控集群同步建立之前刷新 ctl primary, 规避中控切换导致的
    "对非 primary 建立同步" 问题。
    """

    name = __name__
    code = "spider_sync_ctl_master"
    bound_service = SyncCtlMasterService
