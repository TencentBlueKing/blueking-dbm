# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

TenDBHA 集群元数据聚合辅助 · Extractor 侧共享实现。

模块职责：
  - 为 TenDBHA 系"仅携带 ``cluster_ids`` 的单据"（Slave 新机重建 / Slave 添加 / 主从迁移 /
    Proxy 替换 / Proxy 扩容 等）提供一个统一的 Cluster 元数据反查入口，产出 Extractor
    装配 :class:`ResourceGroup` 所需的四件套：``storage_expected_ports`` /
    ``proxy_expected_ports`` / ``cluster_domains`` / ``access_layer_proxies``
  - 不涉及任何 ticket_data 解析、ResourceGroup 构造；上游 Extractor 自行把每个 info 的
    ``cluster_ids`` 传入本函数，拿到纯数据结果后再去装配 :class:`RevokeUnit`

设计要点：
  - **口径契约**：
      · ``storage_expected_ports`` ← 关联集群全部 ``StorageInstance.port`` 去重；
        与 TenDBHA"同集群主从同端口"约束对齐，新 master / 新 slave 共享同一组端口
        （Slave 侧单据 / 主从迁移单据消费此字段）
      · ``proxy_expected_ports``   ← 关联集群全部 ``ProxyInstance.port``（proxy_port 口径）去重；
        扩容 / 替换新 proxy 复用现有 proxy_port（Proxy 侧单据消费此字段）
      · ``cluster_domains``        ← 关联集群 ``immute_domain`` 去重
      · ``access_layer_proxies``   ← 关联集群内 ``status=RUNNING`` 的 :class:`ProxyInstance`
        的 ``(ip, admin_port, bk_cloud_id)``，整条 AccessLayerInstance 去重；
        供 Slave 侧 F2.d 走 proxyrpc 实查 backends（跨组 R3 兜底）
  - 本辅助仅承担 DB 读取；无 ticket_data 字段相关逻辑；入参仅接收已清洗过的
    ``List[int] cluster_ids_i``（上游负责类型规整，本辅助只做"存在性 + 整数"校验）
  - 单次反查全集一次性 ``prefetch_related``（``storageinstance_set`` + 带
    ``status=RUNNING`` 过滤的 ``proxyinstance_set``），全程 2 条 SQL，无 N+1

模块边界：
  - ``cluster_ids`` 空列表 / 非 list / 内含非整型 → 抛 :class:`NormalTenDBFlowException`
  - DBM 元数据查不到任何 Cluster（全删） → 抛 :class:`NormalTenDBFlowException`
  - 查到的 Cluster 数量 < 去重后的入参长度（部分已删） → 抛 :class:`NormalTenDBFlowException`
  - 关联集群不存在任何 ``StorageInstance`` / RUNNING proxy → 对应字段返回空 tuple（允许，由上游决定）
  - 异常一律由上层 ``revoke_flow`` 顶层 try/except 统一兜底，本模块不做局部吞异常
"""
from typing import Any, Dict, List, Tuple

from django.db.models import Prefetch, QuerySet

from backend.db_meta.enums import InstanceStatus
from backend.db_meta.models import Cluster, ProxyInstance
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import NormalTenDBFlowException
from backend.flow.engine.bamboo.scene.mysql.revoke.base.models import AccessLayerInstance


def load_tendbha_cluster_meta(cluster_ids: List[int], err_prefix: str, info_idx: int) -> Dict[str, Any]:
    """反查 TenDBHA 集群元数据，产出 Extractor 组装所需四件套。

    设计要点 / 怎么做：
      - 使用 ``prefetch_related`` + ``Prefetch(..., queryset=... .select_related("machine"))``
        一次性预加载 ``storageinstance_set`` 与 RUNNING ``proxyinstance_set``，避免 N+1
      - 端口口径分离：
          · ``storage_expected_ports`` ← 全部 ``StorageInstance.port`` 去重（Slave 侧消费）
          · ``proxy_expected_ports``   ← 全部 ``ProxyInstance.port`` 去重（Proxy 侧消费）
      - proxy 聚合：按整条 ``AccessLayerInstance`` 跨集群去重，port 填 ``admin_port``；
        与 F2.d 探测契约对齐（mysql-proxy 对 ``SELECT * FROM backends;`` 只在 admin port 上响应）

    :param cluster_ids: 上游传入的 ``info["cluster_ids"]``；期望为 ``List[int]``
    :param err_prefix: 错误消息前缀，用于区分调用方（如 "[MysqlRestoreSlaveExtractor]"）
    :param info_idx: info 在 infos 中的索引，用于错误消息定位
    :return: dict，字段：
        - ``cluster_domains``:        ``Tuple[str, ...]`` 关联集群 ``immute_domain`` 去重
        - ``clb_regions``:            ``Tuple[str, ...]`` 关联集群 ``region`` 字段去重（供 F2.b
          CLB 校验使用；元素为 ``cluster.region`` 字符串，可能为中文地名"南京"或腾讯云 region
          代号"ap-nanjing"，具体取决于集群创建时写入的口径——下游 ``check_clb_mapping`` 比对
          ``ip + clbid`` 不比对 region 字段，二者兼容）
        - ``storage_expected_ports``: ``Tuple[int, ...]`` 关联集群全部 ``StorageInstance.port`` 去重
        - ``proxy_expected_ports``:   ``Tuple[int, ...]`` 关联集群全部 ``ProxyInstance.port`` 去重（proxy_port 口径）
        - ``access_layer_proxies``:   ``Tuple[AccessLayerInstance, ...]`` RUNNING proxy
          的 ``(ip, admin_port, bk_cloud_id)`` 去重

    边界：
      - cluster_ids 非 list / 空 / 内含非整型 → 抛 :class:`NormalTenDBFlowException`
      - DBM 元数据查不到任何 Cluster → 抛 :class:`NormalTenDBFlowException`
      - 部分 cluster 已删除（结果数 < 去重入参长度）→ 抛 :class:`NormalTenDBFlowException`
    """

    clusters_qs: QuerySet = Cluster.objects.filter(id__in=cluster_ids).prefetch_related(
        "storageinstance_set__machine",
        Prefetch(
            "proxyinstance_set",
            queryset=ProxyInstance.objects.filter(status=InstanceStatus.RUNNING.value).select_related("machine"),
        ),
    )
    clusters: List[Cluster] = list(clusters_qs)

    if not clusters:
        raise NormalTenDBFlowException(
            message="{} infos[{}] cluster_ids={} all removed from DBM meta (empty queryset)".format(
                err_prefix, info_idx, cluster_ids
            )
        )
    if len(clusters) < len(set(cluster_ids)):
        found_ids = {c.id for c in clusters}
        missing_ids = set(cluster_ids) - found_ids
        raise NormalTenDBFlowException(
            message="{} infos[{}] cluster_ids partially removed, missing={}".format(
                err_prefix, info_idx, sorted(missing_ids)
            )
        )

    # 聚合存储实例端口（set 一次性去重）：新 master / 新 slave 与集群内其他 storage 共享同一组端口
    # 依据：TenDBHA 架构"同集群主从同端口"约束，端口由 cluster_ids 关联集群在 DBM 元数据登记
    # 走 .all() 而非 .first()：前者命中上面 prefetch_related 缓存无额外 SQL，后者会单对象返回且绕过缓存
    storage_expected_ports: Tuple[int, ...] = tuple(
        {int(s.port) for c in clusters for s in c.storageinstance_set.all()}
    )

    # 聚合 proxy 端口（proxy_port 口径，非 admin_port）：扩容 / 替换新 proxy 复用现有 proxy_port
    # 走 .all() 直接命中上面 Prefetch(status=RUNNING) 预取结果，无额外 SQL
    proxy_expected_ports: Tuple[int, ...] = tuple({int(p.port) for c in clusters for p in c.proxyinstance_set.all()})

    # 聚合 immute_domain：按集合去重；集合天然不保序，保持与"端口 set 去重"相同的无序口径
    cluster_domains: Tuple[str, ...] = tuple({c.immute_domain for c in clusters if c.immute_domain})

    # 聚合 Cluster.region：供 F2.b CLB 校验使用。
    # 口径：业务层中 Cluster.region 等同于 CLB 创建时使用的 region（见 mysql_clb.create_lb_and_register_target
    # 直接 region = cluster.region），因此直接读 Cluster 自带字段即可，不需额外查 CLBEntryDetail。
    # 空字符串由 ``if c.region`` 过滤；集合天然去重 + 保持无序口径
    clb_regions: Tuple[str, ...] = tuple({c.region for c in clusters if c.region})

    # 聚合 RUNNING proxy 实例：按整条 AccessLayerInstance 跨集群去重；
    # AccessLayerInstance 是 frozen dataclass 天然可哈希，直接走 set 推导。
    # port 必须填 admin_port，F2.d 走 proxyrpc 发 ``SELECT * FROM backends;`` 只在 admin port 响应。
    # 这里 c.proxyinstance_set.all() 命中上面 Prefetch 预取的 RUNNING + machine 缓存，无额外 SQL
    access_layer_proxies: Tuple[AccessLayerInstance, ...] = tuple(
        {
            AccessLayerInstance(
                ip=str(p.machine.ip),
                port=int(p.admin_port),
                bk_cloud_id=int(p.machine.bk_cloud_id),
            )
            for c in clusters
            for p in c.proxyinstance_set.all()
        }
    )

    return {
        "cluster_domains": cluster_domains,
        "clb_regions": clb_regions,
        "storage_expected_ports": storage_expected_ports,
        "proxy_expected_ports": proxy_expected_ports,
        "access_layer_proxies": access_layer_proxies,
    }


def validate_host_dict(host: Any, err_prefix: str, info_idx: int, field_name: str) -> None:
    """校验主机 dict 必须含 ``ip`` / ``bk_host_id`` 两字段。

    :param host: 待校验的主机字典（期望含 ``ip`` / ``bk_host_id`` / ``bk_cloud_id``）
    :param err_prefix: 错误消息前缀
    :param info_idx: info 在 infos 中的索引（用于错误定位）
    :param field_name: info 中的字段名（如 ``bk_new_slave`` / ``new_slave``）
    :return: None
    边界：host 非 dict / 缺 ip / 缺 bk_host_id → 抛 :class:`NormalTenDBFlowException`
    """
    if not isinstance(host, dict):
        raise NormalTenDBFlowException(
            message="{} infos[{}].{} is not dict: {!r}".format(err_prefix, info_idx, field_name, host)
        )
    if "ip" not in host or "bk_host_id" not in host:
        raise NormalTenDBFlowException(
            message="{} infos[{}].{} missing ip/bk_host_id: {!r}".format(err_prefix, info_idx, field_name, host)
        )
