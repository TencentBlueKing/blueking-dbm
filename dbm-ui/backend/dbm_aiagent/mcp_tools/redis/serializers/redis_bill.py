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

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.spec import SpecMachineType
from backend.flow.consts import ClusterRoleEnum, DbBackupRoleEnum, RedisBackupEnum

_REDIS_SPEC_MACHINE_TYPES = (
    SpecMachineType.PROXY.value,
    SpecMachineType.TendisTwemproxyRedisInstance.value,
    SpecMachineType.TendisPredixyTendisplusCluster.value,
    SpecMachineType.TwemproxyTendisSSDInstance.value,
)


class SubmitBillOutputSerializer(serializers.Serializer):
    bill_id = serializers.IntegerField(help_text=_("单据id, 理论上都会返回，如果没有返回说明有错误，需要把错误暴露出来"))
    bill_url = serializers.URLField(help_text=_("单据链接"))


class ListRedisSpecsInputSerializer(serializers.Serializer):
    """列出 desc（备注）中含 mcp_allow（大小写不敏感）的 Redis 规格，供 apply 选型。"""

    machine_type = serializers.ChoiceField(
        choices=_REDIS_SPEC_MACHINE_TYPES,
        required=False,
        allow_blank=True,
        default="",
        help_text=_(
            "可选。过滤机器类型：proxy（代理层，Twemproxy/Predixy通用）、"
            "TwemproxyRedisInstance（TendisCache后端，RedisCluster架构复用此规格）、"
            "PredixyTendisplusCluster（Tendisplus后端）、TwemproxyTendisSSDInstance（TendisSSD后端）；"
            "不传则四类都返回"
        ),
    )


class ListRedisSpecsOutputSerializer(serializers.Serializer):
    results = serializers.ListField(child=serializers.DictField(), help_text=_("规格列表"))
    count = serializers.IntegerField(help_text=_("数量"))


class SubmitBillRedisBaseInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id, bk_biz_id"))
    cluster_domain = serializers.CharField(help_text=_("集群域名，，格式为xx.xx.xx.db"))


class SubmitBillRedisClusterApplyInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id, bk_biz_id"))
    cluster_domain = serializers.CharField(help_text=_("参照部署参数的已有集群域名，格式为xx.xx.xx.db"))
    new_cluster_name = serializers.CharField(help_text=_("新集群名（英文数字及连字符，不能与已有集群重名）"))
    keep_source_password = serializers.BooleanField(
        help_text=_("新集群密码是否与源集群保持一致，默认 False（生成新随机密码）"),
        default=False,
        required=False,
    )


class SubmitBillRedisClusterNewApplyInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id, bk_biz_id"))
    cluster_name = serializers.CharField(help_text=_("新集群名（英文数字及连字符，不能与同类型的已有集群重名）"))
    cluster_alias = serializers.CharField(help_text=_("集群别名，用于页面展示，不传默认与cluster_name一致"), required=False, default=None)
    cluster_type = serializers.ChoiceField(
        choices=ClusterType.get_choices(),
        help_text=_(
            "集群架构类型，仅支持带proxy层的架构，其余类型运行时会被拒绝："
            "TendisTwemproxyRedisInstance(Twemproxy+RedisCache)、"
            "TwemproxyTendisSSDInstance(Twemproxy+TendisSSD)、"
            "TendisPredixyRedisCluster(Predixy+RedisCluster)、"
            "TendisPredixyTendisplusCluster(Predixy+Tendisplus集群版)、"
            "TendisPredixyTendisplusInstance(Predixy+Tendisplus主从版)"
        ),
    )
    db_version = serializers.CharField(
        help_text=_("后端存储部署版本，需与cluster_type匹配，如 Redis-6.2.7（Cache类）、Tendisplus-2.7.6（Tendisplus类）")
    )
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域id，默认0（表示直连区域）"), default=0, required=False)
    city_code = serializers.CharField(
        help_text=_("城市代码（机器所在城市，用于资源池选机），不传或传空则不限城市"),
        default="",
        allow_blank=True,
        required=False,
    )
    disaster_tolerance_level = serializers.ChoiceField(
        choices=AffinityEnum.get_choices(),
        help_text=_(
            "容灾要求（机器亲和性策略），影响资源池选机的分布策略，默认NONE（无要求）。可选值："
            "SAME_SUBZONE_CROSS_SWTICH(指定园区)、SAME_SUBZONE(指定园区，无机架要求)、"
            "CROS_SUBZONE(跨园区)、CROSS_RACK(不限园区)、NONE(无)、"
            "MAX_EACH_ZONE_EQUAL(每个subzone尽量均匀分布)"
        ),
        default=AffinityEnum.NONE.value,
        required=False,
    )
    proxy_spec_id = serializers.IntegerField(help_text=_("proxy层机器的资源规格id（需为平台中已存在的有效规格id，可参照已有同类型集群的规格获取）"))
    proxy_count = serializers.IntegerField(help_text=_("proxy机器数量，至少2台，否则单据会被拒绝"))
    backend_spec_id = serializers.IntegerField(help_text=_("后端存储（redis）机器的资源规格id（需为平台中已存在的有效规格id，可参照已有同类型集群的规格获取）"))
    group_num = serializers.IntegerField(help_text=_("后端机器组数，即master机器数（master去重后的机器对数），至少为1"))
    shard_num = serializers.IntegerField(
        help_text=_(
            "集群总分片数（master实例总数）；不能小于group_num；"
            "当cluster_type为TendisPredixyRedisCluster或TendisPredixyTendisplusCluster（集群协议类型）时，要求 >= 3"
        )
    )
    proxy_pwd = serializers.CharField(
        help_text=_("proxy访问密码，不传或传空则自动生成满足密码强度策略的随机密码"),
        required=False,
        allow_blank=True,
        default=None,
    )
    port = serializers.IntegerField(help_text=_("proxy监听端口，默认50000"), default=50000, required=False)
    apply_clb = serializers.BooleanField(
        help_text=_("是否同时为集群申请并绑定CLB（腾讯云负载均衡）用于访问入口，默认False（不申请）"),
        default=False,
        required=False,
    )
    apply_polaris = serializers.BooleanField(
        help_text=_("是否同时为集群申请并绑定北极星服务用于访问入口，默认False（不申请）"),
        default=False,
        required=False,
    )


class SubmitBillRedisInsApplyInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id, bk_biz_id"))
    cluster_domain = serializers.CharField(help_text=_("参照部署参数的已有主从集群域名，格式为xx.xx.xx.db"))
    new_cluster_name = serializers.CharField(help_text=_("新集群名（英文数字及连字符，不能与已有集群重名）"))
    spec_id = serializers.IntegerField(
        help_text=_("全新机器部署（资源池）时使用的机器规格id；当传入 master_ip 走追加部署模式时本参数忽略"),
        required=False,
        default=None,
    )
    keep_source_password = serializers.BooleanField(
        help_text=_("新集群密码是否与源集群保持一致，默认 False（生成新随机密码）"),
        default=False,
        required=False,
    )
    master_ip = serializers.IPAddressField(
        help_text=_(
            "可选，指定cluster_domain集群下某个已有master的IP，在其所在主机对（该master及其对应slave）上" "追加部署新的redis主从实例（不占用新机器）；不传时默认使用资源池全新机器部署"
        ),
        required=False,
        allow_null=True,
        default=None,
    )


class SubmitBillRedisFullBackupInputSerializer(SubmitBillRedisBaseInputSerializer):
    backup_type = serializers.ChoiceField(
        choices=RedisBackupEnum.get_choices(), default=RedisBackupEnum.NORMAL_BACKUP, help_text=_("备份类型")
    )
    target = serializers.ChoiceField(
        choices=DbBackupRoleEnum.get_choices(), default=DbBackupRoleEnum.Slave, help_text=_("备份对象")
    )


class SubmitBillRedisProxyReduceOrIncreaseInputSerializer(SubmitBillRedisBaseInputSerializer):
    proxy_change_count = serializers.IntegerField(help_text=_("proxy变动数量, 正整数"))


class SubmitBillRedisProxyReduceByIpInputSerializer(SubmitBillRedisBaseInputSerializer):
    reduce_ips = serializers.ListField(child=serializers.CharField(), help_text=_("指定下架proxy的IP列表"))


class SubmitBillRedisFlushDBInputSerializer(SubmitBillRedisBaseInputSerializer):
    is_force = serializers.BooleanField(help_text=_("是否强制清档"), default=False)
    is_backup = serializers.BooleanField(help_text=_("是否需要备份"), default=True)


class SubmitBillRedisExtractKeyInputSerializer(SubmitBillRedisBaseInputSerializer):
    black_regex = serializers.CharField(
        help_text=_("需要排除的key正则，如果是前缀格式为^xxx, 如果是后缀格式为xxx$, 如果要匹配所有是*，如果排除具体key,则是^xxx$。多个正则之间以'\n'换行符连接"),
        default="",
        allow_blank=True,
    )
    white_regex = serializers.CharField(
        help_text=_("需要匹配的key正则，如果是前缀格式为^xxx, 如果是后缀格式为xxx$, 如果要匹配所有是*，如果匹配具体key,则是^xxx$。多个正则之间以'\n'换行符连接"),
        default="",
        allow_blank=True,
    )


class SubmitBillRedisDeleteKeyInputSerializer(SubmitBillRedisExtractKeyInputSerializer):
    delete_rate = serializers.IntegerField(help_text=_("每秒删除key个数"), default="200")


class SubmitBillRedisCutoffInputSerializer(SubmitBillRedisBaseInputSerializer):
    cutoff_ips = serializers.ListField(child=serializers.CharField(), help_text=_("需要整机替换的ip列表"))


class SubmitBillRedisClusterScaleInputSerializer(SubmitBillRedisBaseInputSerializer):
    target_group_num = serializers.IntegerField(help_text=_("集群目标机器组数"))


class SubmitBillRedisLoadModulesInputSerializer(SubmitBillRedisBaseInputSerializer):
    modules = serializers.ListField(
        child=serializers.CharField(), help_text=_("需要安装的插件列表，目前只支持redisbloom、redisell、redisjson")
    )


class SubmitBillRedisKeyStatInputSerializer(SubmitBillRedisBaseInputSerializer):
    ins = serializers.ListField(child=serializers.CharField(), help_text=_("需要分析的实例列表"))


class SubmitBillRedisAnalysisHotkeyInputSerializer(SubmitBillRedisBaseInputSerializer):
    analysis_time = serializers.IntegerField(help_text=_("分析时长，单位为秒。只允许10、30、60"), default="10")
    ins = serializers.ListField(child=serializers.CharField(), help_text=_("需要分析的实例列表。默认只分析proxy角色，除非指定实例"))


class SubmitBillRedisVersionUpdateInputSerializer(SubmitBillRedisBaseInputSerializer):
    node_type = serializers.ChoiceField(choices=ClusterRoleEnum.get_choices(), help_text=_("升级角色，Proxy|Backend"))
    target_version = serializers.CharField(
        help_text="目标版本，格式为：twemproxy-0.4.1-v36|predixy-1.6.1|redis-6.2.7" "|tendisplus-2.7.6-rocksdb-v8.5.3"
    )


class SubmitBillRedisMasterSlaveSwitchInputSerializer(SubmitBillRedisBaseInputSerializer):
    """Redis主从切换序列化器"""

    master_ips = serializers.ListField(
        child=serializers.IPAddressField(), help_text=_("要切换的master IP列表"), min_length=1
    )
