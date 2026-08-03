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


class HostPerformanceByIpInputSerializer(serializers.Serializer):
    ip = serializers.CharField(help_text=_("主机 IP，与 bk_cloud_id 一起唯一定位 Machine"))
    bk_cloud_id = serializers.IntegerField(
        required=False,
        default=0,
        help_text=_("云区域 ID，默认 0"),
    )


class HostMachineSummarySerializer(serializers.Serializer):
    ip = serializers.CharField(help_text=_("主机 IP"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    bk_svr_device_cls_name = serializers.CharField(
        allow_blank=True,
        help_text=_("CMDB/资源池标准设备类型名，用于关联 BaselineHost.device_class；可能为空字符串"),
    )


class HostBaselineOutputSerializer(serializers.Serializer):
    device_class = serializers.CharField(help_text=_("基线机型编码，对应 BaselineHost.device_class"))
    cpu_model = serializers.CharField(help_text=_("CPU 型号"))
    cpu_frequency_ghz = serializers.FloatField(
        allow_null=True,
        help_text=_("CPU 主频或全核睿频，单位 GHz；无数据时为 null"),
    )
    network_card_speed = serializers.CharField(
        allow_blank=True,
        help_text=_("网卡速度描述，如 100G；无数据时可能为空字符串"),
    )
    vcpu = serializers.IntegerField(help_text=_("vCPU 核数"))
    memory_gb = serializers.IntegerField(help_text=_("内存容量，单位 GB"))
    network_pps_w = serializers.IntegerField(
        allow_null=True,
        help_text=_("网络收发包能力，单位万 pps；无数据时为 null"),
    )
    intranet_bandwidth_gbps = serializers.FloatField(
        allow_null=True,
        help_text=_("内网带宽能力，单位 Gbps；无数据时为 null"),
    )
    queue_count = serializers.IntegerField(
        allow_null=True,
        help_text=_("主机硬件队列数；无数据时为 null"),
    )


class DiskBaselineOutputSerializer(serializers.Serializer):
    disk_name = serializers.CharField(help_text=_("基线磁盘配置唯一名称"))
    disk_type = serializers.CharField(help_text=_("磁盘类型枚举值，与 Machine.storage_device 中 disk_type 同源"))
    capacity_gb = serializers.IntegerField(
        allow_null=True,
        help_text=_("基线单盘容量，单位 GB；无数据时为 null"),
    )
    performance_iops = serializers.IntegerField(
        allow_null=True,
        help_text=_("基线 IOPS；无数据时为 null"),
    )
    performance_throughput_mbps = serializers.IntegerField(
        allow_null=True,
        help_text=_("基线吞吐，单位 MB/s；无数据时为 null"),
    )
    random_read_iops = serializers.IntegerField(
        allow_null=True,
        help_text=_("随机读 IOPS；无数据时为 null"),
    )
    sequential_write_throughput_mbps = serializers.IntegerField(
        allow_null=True,
        help_text=_("顺序写吞吐，单位 MB/s；无数据时为 null"),
    )
    write_latency_ms = serializers.FloatField(
        allow_null=True,
        help_text=_("写延迟，单位 ms；无数据时为 null"),
    )


class HostDiskRowOutputSerializer(serializers.Serializer):
    mount_point = serializers.CharField(help_text=_("挂载点路径，来自 Machine.storage_device 的键"))
    disk_type = serializers.CharField(
        allow_blank=True,
        help_text=_("磁盘类型，与元数据 storage_device 中 disk_type 一致；空表示未上报"),
    )
    size = serializers.IntegerField(
        allow_null=True,
        help_text=_("该挂载点容量，单位 GB，来自元数据；未上报时为 null"),
    )
    baseline = DiskBaselineOutputSerializer(
        allow_null=True,
        required=False,
        help_text=_("按 disk_type 与 size 匹配到的磁盘基线性能；无类型、无基线数据或未匹配时为 null"),
    )


class SingleHostPerformanceOutputSerializer(serializers.Serializer):
    machine = HostMachineSummarySerializer(
        allow_null=True,
        required=False,
        help_text=_("主机定位摘要；无此 ip+云区域主机时为 null"),
    )
    host_baseline = HostBaselineOutputSerializer(
        allow_null=True,
        required=False,
        help_text=_("机型在 BaselineHost 中的性能子集；机型无基线配置时为 null"),
    )
    disks = HostDiskRowOutputSerializer(
        many=True,
        help_text=_("各挂载点磁盘及匹配基线；无主机或 storage_device 为空时为 []"),
    )


class ClusterHostItemOutputSerializer(SingleHostPerformanceOutputSerializer):
    """集群下每台主机一行：在单机性能结构基础上附带本集群内的实例角色。"""

    instance_roles = serializers.ListField(
        child=serializers.CharField(),
        help_text=_("该主机在本集群中出现的实例角色（去重排序）：" "取自 StorageInstance.instance_role 非空值；若本机在集群上存在 ProxyInstance 则包含 proxy"),
    )


class HostPerformanceByClusterInputSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text=_("集群主键 ID；与 cluster_domain 二选一，不可同时传"),
    )
    cluster_domain = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=_("集群 immute 域名；与 cluster_id 二选一，不可同时传"),
    )
    instance_roles = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text=_("可选实例角色过滤：StorageInstance.instance_role 取值或包含 proxy 时表示纳入 Proxy 所在机器；" "不传或空列表表示集群下全部存储与代理实例所在机器"),
    )

    def validate(self, attrs):
        cluster_id = attrs.get("cluster_id")
        cluster_domain = (attrs.get("cluster_domain") or "").strip()
        has_id = cluster_id is not None
        has_domain = bool(cluster_domain)
        if not has_id and not has_domain:
            raise serializers.ValidationError(_("必须提供 cluster_id 或 cluster_domain 之一"))
        if has_id and has_domain:
            raise serializers.ValidationError(_("cluster_id 与 cluster_domain 不能同时提供"))
        if has_domain:
            attrs["cluster_domain"] = cluster_domain
        return attrs


class ClusterHostPerformanceOutputSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群 ID"))
    immute_domain = serializers.CharField(help_text=_("集群 immute 域名"))
    hosts = ClusterHostItemOutputSerializer(
        many=True,
        help_text=_("去重后的各主机性能数据：在单机查询结构基础上含 instance_roles；过滤后无机器时为 []"),
    )


class HostInstancePortsMachineSerializer(serializers.Serializer):
    ip = serializers.CharField(help_text=_("主机 IP"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))


class HostInstancePortsOutputSerializer(serializers.Serializer):
    machine = HostInstancePortsMachineSerializer(
        allow_null=True,
        required=False,
        help_text=_("命中 DBM Machine 时为 ip 与 bk_cloud_id；无主机时为 null"),
    )
    instance_count = serializers.IntegerField(
        help_text=_("该机上的存储实例与代理实例条数之和（StorageInstance + ProxyInstance）"),
    )
    ports = serializers.ListField(
        child=serializers.IntegerField(),
        help_text=_("上述实例的监听端口，合并后升序去重；无实例时为 []"),
    )


class ClusterRefHostInputSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text=_("集群主键 ID；与 cluster_domain 二选一，不可同时传"),
    )
    cluster_domain = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=_("集群 immute 域名；与 cluster_id 二选一，不可同时传"),
    )

    def validate(self, attrs):
        cluster_id = attrs.get("cluster_id")
        cluster_domain = (attrs.get("cluster_domain") or "").strip()
        has_id = cluster_id is not None
        has_domain = bool(cluster_domain)
        if not has_id and not has_domain:
            raise serializers.ValidationError(_("必须提供 cluster_id 或 cluster_domain 之一"))
        if has_id and has_domain:
            raise serializers.ValidationError(_("cluster_id 与 cluster_domain 不能同时提供"))
        if has_domain:
            attrs["cluster_domain"] = cluster_domain
        return attrs


class RefSpiderHostOutputSerializer(serializers.Serializer):
    """Spider 参考主机平铺结构：machine / host_baseline 展开为单层字段。"""

    ref_role = serializers.CharField(help_text=_("参考角色：spider_master"))
    ip = serializers.CharField(allow_null=True, help_text=_("主机 IP"))
    bk_cloud_id = serializers.IntegerField(allow_null=True, help_text=_("云区域 ID"))
    bk_svr_device_cls_name = serializers.CharField(
        allow_blank=True,
        help_text=_("CMDB/资源池标准设备类型名"),
    )
    device_class = serializers.CharField(allow_null=True, allow_blank=True, help_text=_("基线机型编码"))
    cpu_model = serializers.CharField(allow_null=True, allow_blank=True, help_text=_("CPU 型号"))
    cpu_frequency_ghz = serializers.FloatField(allow_null=True, help_text=_("CPU 主频，单位 GHz"))
    network_card_speed = serializers.CharField(allow_null=True, allow_blank=True, help_text=_("网卡速度描述"))
    vcpu = serializers.IntegerField(allow_null=True, help_text=_("vCPU 核数"))
    memory_gb = serializers.IntegerField(allow_null=True, help_text=_("内存容量，单位 GB"))
    network_pps_w = serializers.IntegerField(allow_null=True, help_text=_("网络 pps，单位万"))
    intranet_bandwidth_gbps = serializers.FloatField(allow_null=True, help_text=_("内网带宽，单位 Gbps"))
    queue_count = serializers.IntegerField(allow_null=True, help_text=_("主机硬件队列数"))


class RefStorageHostOutputSerializer(RefSpiderHostOutputSerializer):
    """
    存储参考主机平铺结构：在主机基线平铺基础上，附加 instance_count 与 datadir 匹配磁盘基线。
    """

    ref_role = serializers.CharField(help_text=_("参考角色：backend_master / orphan / remote_master"))
    instance_count = serializers.IntegerField(
        help_text=_("该存储代表机上的 StorageInstance 数量（同机部署密度，不含 Proxy）"),
    )
    datadir = serializers.CharField(allow_blank=True, help_text=_("实例 datadir 原始路径；查询失败时为空"))
    data_dir_mount = serializers.CharField(
        allow_blank=True,
        help_text=_("由 datadir 推导的数据盘挂载点，如 /data1；无法匹配时为空"),
    )
    mount_point = serializers.CharField(
        allow_null=True,
        allow_blank=True,
        help_text=_("匹配到的主机磁盘挂载点；未匹配时为 null"),
    )
    disk_type = serializers.CharField(allow_null=True, allow_blank=True, help_text=_("匹配磁盘类型"))
    size = serializers.IntegerField(allow_null=True, help_text=_("匹配磁盘容量 GB"))
    disk_name = serializers.CharField(allow_null=True, allow_blank=True, help_text=_("磁盘基线名称"))
    capacity_gb = serializers.IntegerField(allow_null=True, help_text=_("磁盘基线容量 GB"))
    performance_iops = serializers.IntegerField(allow_null=True, help_text=_("磁盘基线 IOPS"))
    performance_throughput_mbps = serializers.IntegerField(
        allow_null=True,
        help_text=_("磁盘基线吞吐，单位 MB/s"),
    )
    random_read_iops = serializers.IntegerField(allow_null=True, help_text=_("随机读 IOPS"))
    sequential_write_throughput_mbps = serializers.IntegerField(
        allow_null=True,
        help_text=_("顺序写吞吐，单位 MB/s"),
    )
    write_latency_ms = serializers.FloatField(allow_null=True, help_text=_("写延迟，单位 ms"))


class ClusterRefHostPerfOutputSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群 ID"))
    immute_domain = serializers.CharField(help_text=_("集群 immute 域名"))
    cluster_type = serializers.CharField(help_text=_("集群类型：tendbsingle / tendbha / tendbcluster"))
    ref_shard_id = serializers.IntegerField(
        allow_null=True,
        help_text=_("TenDBCluster 采样分片号（最小 shard_id）；TenDBHA/TenDBSingle 为 null"),
    )
    spider_host = RefSpiderHostOutputSerializer(
        allow_null=True,
        help_text=_("TenDBCluster 一台 spider_master 平铺主机性能；TenDBHA/TenDBSingle 为 null"),
    )
    storage_host = RefStorageHostOutputSerializer(
        allow_null=True,
        help_text=_(
            "存储代表机平铺性能：TenDBSingle 为 orphan；TenDBHA 为 backend_master；"
            "TenDBCluster 为首分片 remote_master；含 datadir 匹配后的数据盘基线字段"
        ),
    )
