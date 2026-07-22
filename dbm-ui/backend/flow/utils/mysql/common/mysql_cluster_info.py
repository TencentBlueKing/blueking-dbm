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
from typing import Any, Dict, List

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.mysql.mysql_os_timezone_init import MySQLInitOsTimeZoneKwargs


def get_version_and_charset(bk_biz_id, db_module_id, cluster_type) -> Any:
    """
    获取指定业务模块下的数据库版本号和字符集信息。

    Args:
        bk_biz_id (int or str): 业务ID
        db_module_id (int or str): 模块ID
        cluster_type (str): 集群类型（如 "tendbcluster"）

    Returns:
        tuple: (charset, db_version)
            charset (str): 字符集信息
            db_version (str): 数据库版本号
    """
    data = DBConfigApi.query_conf_item(
        {
            "bk_biz_id": str(bk_biz_id),
            "level_name": LevelName.MODULE,
            "level_value": str(db_module_id),
            "conf_file": "deploy_info",
            "conf_type": "deploy",
            "namespace": cluster_type,
            "format": FormatType.MAP,
        }
    )["content"]
    return data["charset"], data["db_version"]


def get_cluster_ports(cluster_ids: list) -> Dict:
    cluster_ports = []
    cluster_list = []
    clusters = Cluster.objects.filter(id__in=cluster_ids).all()
    clustertmp = clusters[0]
    db_module_id = clustertmp.db_module_id
    cluster_type = clustertmp.cluster_type
    bk_cloud_id = clustertmp.bk_cloud_id
    time_zone = clustertmp.time_zone
    for one_cluster in clusters:
        master = one_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
        cluster_port = master.port
        cluster_ports.append(cluster_port)
        cluster_list.append(
            {
                "master_ip": master.machine.ip,
                "mysql_port": cluster_port,
                "name": one_cluster.name,
                "master": one_cluster.immute_domain,
                "cluster_id": one_cluster.id,
                "bk_cloud_id": one_cluster.bk_cloud_id,
            }
        )
    cluster_info = {
        "cluster_ports": cluster_ports,
        "clusters": cluster_list,
        "db_module_id": db_module_id,
        "cluster_type": cluster_type,
        "bk_cloud_id": bk_cloud_id,
        "time_zone": time_zone,
    }
    return cluster_info


def get_ports(cluster_ids: list) -> list:
    cluster_ports = []
    clusters = Cluster.objects.filter(id__in=cluster_ids).all()
    for cluster in clusters:
        if cluster.cluster_type == ClusterType.TenDBSingle.value:
            cluster_ports.append(
                cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.ORPHAN.value).port
            )
        else:
            cluster_ports.append(
                cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value).port
            )
    return cluster_ports


def get_spider_module_version(bk_biz_id, db_module_id) -> str:
    """
    获取指定业务模块下的spider版本信息。

    Args:
        bk_biz_id (int or str): 业务ID
        db_module_id (int or str): 模块ID

    Returns:
        str: spider_version
    """
    data = DBConfigApi.query_conf_item(
        {
            "bk_biz_id": str(bk_biz_id),
            "level_name": LevelName.MODULE,
            "level_value": str(db_module_id),
            "conf_file": "deploy_info",
            "conf_type": "deploy",
            "namespace": ClusterType.TenDBCluster.value,
            "format": FormatType.MAP,
        }
    )["content"]
    return data["spider_version"]


def get_mysql_init_os_timezone_kwargs(
    cluster: Cluster,
    exec_ip: List[str],
) -> MySQLInitOsTimeZoneKwargs:
    """根据单个 :class:`Cluster` 实例组装 MySQLInitOsTimeZoneComponent 组件的 kwargs。

    设计要点 / 怎么做：
      - 数据源：调用方已持有的 :class:`db_meta.models.Cluster` 实例（本函数不做 ORM 反查）；
      - 通道：纯字段抽取 + 组装，不涉及 pipeline 上下文，也不涉及 dbconfig；
      - **契约先行**：直接返回 :class:`MySQLInitOsTimeZoneKwargs` 实例，实例化时经
        ``ValidateHandler.__post_init__`` 立即校验字段合法性；
      - 时区取值已统一为模块级 ``deploy_info.system_time_zone``，组件每次仅处理单一模块，
        因此本函数只需从 ``cluster`` 中直接抽取 ``(bk_cloud_id, bk_biz_id, db_module_id,
        cluster_type)`` 四个字段即可，无需一致性校验。

    :param cluster: 已就绪的 :class:`Cluster` 实例；调用方通常已在流程上下文里持有，
                    直接传入避免再走一次 ``Cluster.objects.filter(id=...)`` 反查
    :param exec_ip: 目标机器 IP 列表（合法 IPv4 字符串），传给 ``JobApi`` 下发使用
    :return: :class:`MySQLInitOsTimeZoneKwargs` 实例，字段：
             ``bk_cloud_id / exec_ip / bk_biz_id / db_module_id / cluster_type``。
             调用方将其挂到 pipeline ``kwargs`` 时需 ``asdict(...)``，例如：

             .. code-block:: python

                 from dataclasses import asdict
                 tz_kwargs = get_mysql_init_os_timezone_kwargs(cluster=cluster, exec_ip=[...])
                 pipes.add_act(
                     act_name="init os timezone",
                     act_component_code=MySQLInitOsTimeZoneComponent.code,
                     kwargs=asdict(tz_kwargs),
                 )

    边界 / 异常：
      - ``cluster`` 为 None → 抛 ``ValueError``；
      - ``exec_ip`` 为空 → 抛 ``ValueError``；
      - 字段类型不合法（如 ``exec_ip`` 含非法 IPv4 元素、``cluster.db_module_id`` 非 int 等）
        → 由 :class:`MySQLInitOsTimeZoneKwargs` ``__post_init__`` 抛 ``ValueError``。
    """
    if cluster is None:
        raise ValueError("cluster must not be None")
    if not exec_ip:
        raise ValueError("exec_ip must not be empty")

    # 直接从 Cluster 实例抽取字段；单集群天然满足"同 module / 同类型"，无需一致性校验
    return MySQLInitOsTimeZoneKwargs(
        bk_cloud_id=int(cluster.bk_cloud_id),
        exec_ip=exec_ip,
        bk_biz_id=int(cluster.bk_biz_id),
        db_module_id=int(cluster.db_module_id),
        cluster_type=cluster.cluster_type,
    )


def get_mysql_init_os_timezone_kwargs_for_apply(
    bk_biz_id: int,
    bk_cloud_id: int,
    exec_ip: List[str],
    db_module_id: int,
    cluster_type: str,
) -> MySQLInitOsTimeZoneKwargs:
    """部署场景专用：直接依据单据入参组装 MySQLInitOsTimeZoneComponent 组件的 kwargs。

    设计要点 / 怎么做：
      - 与 :func:`get_mysql_init_os_timezone_kwargs` 的区别：**不查 db_meta 元数据**。
        部署（apply）阶段集群尚未落库，无法用 ``cluster_id`` 反查；改由调用方
        （单据 flow 类）直接提供 ``db_module_id / cluster_type`` 两字段
        （这些字段在单据 ticket_data 里已就绪）。
      - **契约先行**：直接返回 :class:`MySQLInitOsTimeZoneKwargs` 实例，实例化时经
        ``ValidateHandler.__post_init__`` 立即校验字段合法性，让错误更早暴露。
      - 组件运行时将**主动请求 dbconfig** 读取 ``deploy_info.system_time_zone``（模块级），
        因此本函数只负责"告诉组件去查哪个 module / cluster_type 的 dbconfig"。

    :param bk_biz_id: 业务 ID，必填
    :param bk_cloud_id: 云区域 ID，必填
    :param exec_ip: 目标机器 IP 列表；每项须为合法 IPv4 字符串，非空
    :param db_module_id: 待部署集群所属的 DB 模块 ID，必填
    :param cluster_type: 待部署集群类型（``tendbha`` / ``tendbsingle`` / ``tendbcluster``），必填

    :return: :class:`MySQLInitOsTimeZoneKwargs` 实例；调用方挂到 pipeline ``kwargs``
             时需 ``asdict(...)``，用法参见 :func:`get_mysql_init_os_timezone_kwargs`。

    边界 / 异常：
      - ``exec_ip`` 为空 → 抛 ``ValueError``；
      - 字段类型不合法（如 ``exec_ip`` 含非法 IPv4、``db_module_id`` 非 int、
        ``cluster_type`` 非 str 等）→ 由 :class:`MySQLInitOsTimeZoneKwargs`
        的 ``__post_init__`` 抛 ``ValueError``；
      - **本函数不做多集群的交叉校验**：调用方（单据 flow）自身语义
        已保证同一单据下的 bk_cloud_id / bk_biz_id / db_module_id / cluster_type 一致。
    """
    if not exec_ip:
        raise ValueError("exec_ip must not be empty")

    # 顶层结构体触发 ValidateHandler.__post_init__，按 field.metadata['validate'] 逐字段校验
    return MySQLInitOsTimeZoneKwargs(
        bk_cloud_id=int(bk_cloud_id),
        exec_ip=exec_ip,
        bk_biz_id=int(bk_biz_id),
        db_module_id=int(db_module_id),
        cluster_type=cluster_type,
    )
