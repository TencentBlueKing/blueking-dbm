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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class _Section_Inputs:
    """分组：MCP 工具的输入字段。

    本组职责
        定义 `sqlserver_sync_status` MCP 工具的入参契约，由 register_mcp_tool
        在请求进入 view 之前完成校验。
    本组类
        - SQLServerSyncStatusInputSerializer
    边界
        - 仅承载入参字段，不做任何业务推断；
        - 该 class 仅作"文档命名空间"使用，不参与运行逻辑，不可实例化。
    字段说明
        - cluster_domain：集群不可变域名，必填；
        - databases：可选的 DB 名白名单，传入后仅返回这些库的同步明细，
          不区分大小写；不传或传空表示全量返回。
    """


class SQLServerSyncStatusInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    databases = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        required=False,
        allow_empty=True,
        default=list,
        help_text=_("可选：指定要分析的数据库名白名单（不区分大小写）。" "不传或传空数组表示返回集群内全部参与同步的数据库；" "用于在大集群下让 LLM 集中分析特定库的同步情况，缩小上下文"),
    )


class _Section_Summary:
    """分组：通用 summary（mirroring / always_on 共用）。

    本组职责
        承载"整体同步健康摘要"字段，供 LLM 第一眼阅读后给出结论性输出。
    本组类
        - SQLServerSyncStatusSummarySerializer
    边界
        - 字段语义对 mirroring / always_on 两种架构同时成立；
        - `node_count`、`max_commit_lag_seconds` 等仅 AG 适用的字段允许为 null；
        - 阈值描述与 impl/sync_status.py:SyncStatusConstants 必须保持同源。
    """


class SQLServerSyncStatusSummarySerializer(serializers.Serializer):
    overall_health = serializers.CharField(
        help_text=_(
            "整体健康度：HEALTHY / PARTIALLY_HEALTHY / NOT_HEALTHY / N/A。" "判定来源：成员同步状态 + 队列阈值 + commit_lag 阈值的综合结果"
        ),
        allow_null=True,
    )
    node_count = serializers.IntegerField(
        help_text=_("AG 副本数；mirroring 不适用此概念，固定为 null"),
        allow_null=True,
    )
    database_count = serializers.IntegerField(help_text=_("参与同步的数据库（视角行）总数"))
    unhealthy_database_count = serializers.IntegerField(help_text=_("被判定为不健康的数据库（视角行）数量"))
    max_log_send_queue_mb = serializers.FloatField(
        help_text=_("全集群最大 log_send_queue（MB）。经验阈值：>=100MB 警告；>=1024MB 严重落后。" "持续高位代表备端追不上主端写入")
    )
    max_redo_queue_mb = serializers.FloatField(help_text=_("全集群最大 redo_queue（MB）。经验阈值同 log_send_queue。代表备端重做日志堆积"))
    max_commit_lag_seconds = serializers.FloatField(
        help_text=_("AG 专属：primary 与 secondary 上 last_commit_time 差的最大值（秒）。" "经验阈值：>=5s 警告；>=60s 严重。可作为 RPO 近似估算"),
        allow_null=True,
    )
    issues = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        help_text=_("顶层问题列表（已聚合各 DB 的关键 issue），LLM 可直接复述"),
    )
    reason = serializers.CharField(
        help_text=_("overall_health=N/A 时的原因说明（如单节点集群、未发现同步关系等）"),
        allow_blank=True,
    )


class _Section_Mirroring:
    """分组：Mirroring 架构详细字段。

    本组职责
        承载 `sys.database_mirroring` + `sys.dm_os_performance_counters` 中
        Database Mirroring 计数器派生出的"每库一行"详细同步信息。
    本组类
        - SQLServerMirroringDatabaseSerializer：单个被镜像数据库的同步明细
        - SQLServerMirroringSectionSerializer：databases 列表的容器
    边界
        - 仅在 `sync_mode=mirroring` 集群上有意义；其他集群整段为 null；
        - 主端视角缺失（仅备端可见）时仍会保留行，便于发现拓扑异常；
        - 速率为 0 时 estimated_*_seconds 为 null，避免被误读为"立即追齐"。
    """


class SQLServerMirroringDatabaseSerializer(serializers.Serializer):
    database_name = serializers.CharField(help_text=_("被镜像的数据库名"), allow_null=True)
    principal_address = serializers.CharField(
        help_text=_("看到该 DB 为 PRINCIPAL 的实例 ip:port；为空表示集群内未发现主端视角"),
        allow_null=True,
    )
    mirror_address = serializers.CharField(
        help_text=_("看到该 DB 为 MIRROR 的实例 ip:port；为空表示备端视角缺失"),
        allow_null=True,
    )
    mirroring_role_desc = serializers.CharField(
        help_text=_("PRINCIPAL / MIRROR；以主端视角为基准"),
        allow_null=True,
    )
    mirroring_state_desc = serializers.CharField(
        help_text=_(
            "SYNCHRONIZED（同步完成）/ SYNCHRONIZING（同步中，异步常态）/ " "SUSPENDED（暂停）/ DISCONNECTED（断连）/ PENDING_FAILOVER（待故障转移）"
        ),
        allow_null=True,
    )
    mirroring_safety_level_desc = serializers.CharField(
        help_text=_("FULL=同步模式（高安全），OFF=异步模式（高性能）"),
        allow_null=True,
    )
    mirroring_witness_state_desc = serializers.CharField(
        help_text=_("见证服务器状态；UNKNOWN / CONNECTED / DISCONNECTED；NULL 表示无见证"),
        allow_null=True,
    )
    # 性能（来自 sys.dm_os_performance_counters）
    log_send_queue_mb = serializers.FloatField(help_text=_("主端待发送日志（MB）。经验阈值：>=100MB 警告；>=1024MB 严重"))
    redo_queue_mb = serializers.FloatField(help_text=_("备端待重做日志（MB）。经验阈值同上"))
    log_send_rate_kbps = serializers.FloatField(help_text=_("当前日志发送速率（KB/s）"))
    redo_rate_kbps = serializers.FloatField(help_text=_("当前 redo 速率（KB/s）"))
    # 派生
    estimated_send_seconds = serializers.FloatField(
        help_text=_("基于当前发送速率估算的清空 log_send_queue 所需秒数；速率为 0 时为 null"),
        allow_null=True,
    )
    estimated_redo_seconds = serializers.FloatField(
        help_text=_("基于当前 redo 速率估算的清空 redo_queue 所需秒数；速率为 0 时为 null"),
        allow_null=True,
    )
    is_healthy = serializers.BooleanField(help_text=_("综合判定：SYNCHRONIZED 且队列 < 警告阈值"))
    issues = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        help_text=_("该 DB 的具体问题列表，例如 state=SUSPENDED / log_send_queue=200MB(warn)"),
    )


class SQLServerMirroringSectionSerializer(serializers.Serializer):
    databases = SQLServerMirroringDatabaseSerializer(
        many=True,
        help_text=_("每个被镜像数据库一行（已合并主备视角并附性能计数器）"),
    )


class _Section_AlwaysOn:
    """分组：AlwaysOn（AG）架构详细字段。

    本组职责
        承载 `sys.availability_*` + `sys.dm_hadr_*` 系列 DMV 派生出的
        "AG → 副本 → DB → Listener / 仲裁成员" 嵌套结构。
    本组类
        - SQLServerAGListenerSerializer：Listener 信息
        - SQLServerAGClusterMemberSerializer：WSFC 仲裁节点信息
        - SQLServerAGDatabaseSerializer：单副本上的单 DB 同步明细
        - SQLServerAGReplicaSerializer：单个副本（聚合其下所有 DB）
        - SQLServerAGSerializer：单个 AG（聚合副本/Listener/仲裁）
        - SQLServerAlwaysOnSectionSerializer：availability_groups 列表的容器
    边界
        - 仅在 `sync_mode=always_on` 集群上有意义；其他集群整段为 null；
        - DB 行的 database_name 可能因副本访问权限而为 null，已用
          dm_hadr_database_replica_cluster_states.database_name 兜底；
        - cluster_members 在小众版本上可能因权限/兼容性返回空列表，不影响整体可用性。
    """


class SQLServerAGListenerSerializer(serializers.Serializer):
    dns_name = serializers.CharField(allow_null=True, help_text=_("Listener DNS 名"))
    port = serializers.IntegerField(allow_null=True, help_text=_("Listener 监听端口"))
    ip_address = serializers.CharField(allow_null=True, help_text=_("VIP"))
    state_desc = serializers.CharField(
        allow_null=True, help_text=_("Listener 状态：ONLINE / OFFLINE / ONLINE_PENDING / FAILED")
    )


class SQLServerAGClusterMemberSerializer(serializers.Serializer):
    member_name = serializers.CharField(allow_null=True, help_text=_("WSFC 节点名"))
    member_state_desc = serializers.CharField(allow_null=True, help_text=_("节点状态：UP / DOWN；DOWN 表示仲裁缺投票"))
    number_of_quorum_votes = serializers.IntegerField(allow_null=True, help_text=_("该节点的仲裁投票数"))


class SQLServerAGDatabaseSerializer(serializers.Serializer):
    database_name = serializers.CharField(allow_null=True, help_text=_("数据库名"))
    replica_server_name = serializers.CharField(allow_null=True, help_text=_("所在副本的服务器名"))
    is_primary_replica = serializers.BooleanField(allow_null=True, help_text=_("是否 primary 副本"))
    synchronization_state_desc = serializers.CharField(
        allow_null=True,
        help_text=_(
            "SYNCHRONIZED（同步完成，仅同步副本会到达）/ SYNCHRONIZING（同步中，"
            "异步副本常态）/ NOT_SYNCHRONIZING（未同步，异常）/ REVERTING / INITIALIZING"
        ),
    )
    synchronization_health_desc = serializers.CharField(
        allow_null=True,
        help_text=_("HEALTHY / PARTIALLY_HEALTHY / NOT_HEALTHY"),
    )
    suspend_reason_desc = serializers.CharField(allow_null=True, help_text=_("挂起原因；正常为 null"))
    is_suspended = serializers.BooleanField(help_text=_("是否被挂起"))
    log_send_queue_mb = serializers.FloatField(help_text=_("主端待发送日志（MB），经验阈值 >=100MB 警告 / >=1024MB 严重"))
    redo_queue_mb = serializers.FloatField(help_text=_("备端待 redo 日志（MB），阈值同上"))
    log_send_rate_kbps = serializers.IntegerField(allow_null=True, help_text=_("发送速率 KB/s"))
    redo_rate_kbps = serializers.IntegerField(allow_null=True, help_text=_("redo 速率 KB/s"))
    last_commit_time = serializers.CharField(
        allow_null=True,
        help_text=_("最近一次 commit 时间；主备相减可近似得到 commit_lag/RPO"),
    )
    estimated_send_seconds = serializers.FloatField(allow_null=True, help_text=_("按当前发送速率估算的清空 log_send_queue 所需秒数"))
    estimated_redo_seconds = serializers.FloatField(allow_null=True, help_text=_("按当前 redo 速率估算的清空 redo_queue 所需秒数"))
    is_failover_ready = serializers.BooleanField(allow_null=True, help_text=_("是否处于可故障转移状态"))
    is_healthy = serializers.BooleanField(help_text=_("综合判定：同步状态正常 + 未挂起 + 队列 < 警告阈值"))
    issues = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        help_text=_("该 DB 的具体问题列表"),
    )


class SQLServerAGReplicaSerializer(serializers.Serializer):
    replica_id = serializers.CharField(allow_null=True, help_text=_("副本 ID（GUID）"))
    replica_server_name = serializers.CharField(allow_null=True, help_text=_("副本所在的实例名"))
    role_desc = serializers.CharField(allow_null=True, help_text=_("PRIMARY / SECONDARY / RESOLVING"))
    availability_mode_desc = serializers.CharField(
        allow_null=True,
        help_text=_("SYNCHRONOUS_COMMIT（同步提交）/ ASYNCHRONOUS_COMMIT（异步提交）"),
    )
    failover_mode_desc = serializers.CharField(allow_null=True, help_text=_("AUTOMATIC / MANUAL（仅同步副本可选 AUTOMATIC）"))
    operational_state_desc = serializers.CharField(
        allow_null=True,
        help_text=_("PENDING_FAILOVER / PENDING / ONLINE / OFFLINE / FAILED 等"),
    )
    connected_state_desc = serializers.CharField(allow_null=True, help_text=_("CONNECTED / DISCONNECTED"))
    synchronization_health_desc = serializers.CharField(
        allow_null=True, help_text=_("副本级同步健康：HEALTHY / PARTIALLY_HEALTHY / NOT_HEALTHY")
    )
    databases = SQLServerAGDatabaseSerializer(many=True, help_text=_("该副本上各 DB 的同步状态"))


class SQLServerAGSerializer(serializers.Serializer):
    ag_name = serializers.CharField(allow_null=True, help_text=_("可用性组名"))
    group_id = serializers.CharField(allow_null=True, help_text=_("AG 的 GUID"))
    primary_replica = serializers.CharField(allow_null=True, help_text=_("当前 primary 副本的实例名"))
    synchronization_health_desc = serializers.CharField(
        allow_null=True,
        help_text=_("AG 整体同步健康：HEALTHY（全部同步副本已同步）/ PARTIALLY_HEALTHY / NOT_HEALTHY"),
    )
    replicas = SQLServerAGReplicaSerializer(many=True, help_text=_("副本列表，primary 在前"))
    listeners = SQLServerAGListenerSerializer(many=True, help_text=_("Listener 列表"))
    cluster_members = SQLServerAGClusterMemberSerializer(many=True, help_text=_("WSFC 仲裁节点列表，用于判断仲裁是否健康"))


class SQLServerAlwaysOnSectionSerializer(serializers.Serializer):
    availability_groups = SQLServerAGSerializer(many=True, help_text=_("可用性组列表"))


class _Section_PerInstance:
    """分组：per-instance 采集结果。

    本组职责
        透出"每个 storage 实例的采集状况"，便于发现部分节点权限不足、网络
        异常等导致的局部失败。
    本组类
        - SQLServerSyncStatusPerInstanceSerializer
    边界
        - error_msg 为空字符串代表该实例采集成功；
        - 单实例失败不会让整体 analyze 失败，仅会反映在本结构上。
    """


class SQLServerSyncStatusPerInstanceSerializer(serializers.Serializer):
    address = serializers.CharField(help_text=_("实例 ip:port"))
    role = serializers.CharField(help_text=_("实例内部角色，例如 master/slave"))
    is_stand_by = serializers.BooleanField(help_text=_("是否备份/standby 角色"))
    error_msg = serializers.CharField(help_text=_("该实例采集错误信息；空字符串表示成功"), allow_blank=True)


class _Section_Output:
    """分组：MCP 工具的顶层输出。

    本组职责
        定义对外返回的最外层结构，组合上述四组（summary / mirroring /
        always_on / per-instance）形成完整契约。
    本组类
        - SQLServerSyncStatusOutputSerializer
    边界
        - mirroring / always_on 互斥：单节点集群两段都为 null；
        - summary 始终存在；overall_health=N/A 时通过 reason 给出原因；
        - 字段顺序对 LLM 阅读体验有影响：summary 优先、详细数据其次、
          per-instance 结果放在最后；
        - filter 字段仅当用户指定 databases 入参时才有意义，否则为 null。
    """


class SQLServerSyncStatusOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    cluster_type = serializers.CharField(help_text=_("集群类型，例如 sqlserver_ha / sqlserver_single"))
    sync_mode = serializers.CharField(
        help_text=_("同步模式：mirroring / always_on；单节点集群为 null"),
        allow_null=True,
    )
    summary = SQLServerSyncStatusSummarySerializer(help_text=_("整体同步健康摘要（LLM 第一眼读这里）"))
    mirroring = SQLServerMirroringSectionSerializer(
        help_text=_("mirroring 详细数据；非 mirroring 集群为 null"),
        allow_null=True,
    )
    always_on = SQLServerAlwaysOnSectionSerializer(
        help_text=_("AlwaysOn 详细数据；非 AG 集群为 null"),
        allow_null=True,
    )
    results = SQLServerSyncStatusPerInstanceSerializer(
        many=True,
        help_text=_("各实例的采集结果，用于发现部分实例采集失败的情况"),
    )
    filter = serializers.DictField(
        required=False,
        allow_null=True,
        help_text=_(
            "用户传入 databases 白名单时回显的过滤情况：包含 requested（原始请求名单，去重后小写）、"
            "matched（在集群中实际命中的库名）、missing（未在集群中找到的库名）。"
            "未指定 databases 入参时为 null"
        ),
    )
