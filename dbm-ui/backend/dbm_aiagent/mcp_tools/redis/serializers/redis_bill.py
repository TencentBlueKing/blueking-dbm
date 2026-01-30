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

from backend.flow.consts import ClusterRoleEnum, DbBackupRoleEnum, RedisBackupEnum


class SubmitBillOutputSerializer(serializers.Serializer):
    bill_id = serializers.IntegerField(help_text=_("单据id, 理论上都会返回，如果没有返回说明有错误，需要把错误暴露出来"))
    bill_url = serializers.URLField(help_text=_("单据链接"))


class SubmitBillRedisBaseInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id, bk_biz_id"))
    cluster_domain = serializers.CharField(help_text=_("集群域名，，格式为xx.xx.xx.db"))


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
    cutoff_ips = serializers.ListField(help_text=_("需要整机替换的ip列表"))


class SubmitBillRedisLoadModulesInputSerializer(SubmitBillRedisBaseInputSerializer):
    modules = serializers.ListField(help_text=_("需要安装的插件列表，目前只支持redisbloom、redisell、redisjson"))


class SubmitBillRedisKeyStatInputSerializer(SubmitBillRedisBaseInputSerializer):
    ins = serializers.ListField(help_text=_("需要分析的实例列表"))


class SubmitBillRedisAnalysisHotkeyInputSerializer(SubmitBillRedisBaseInputSerializer):
    analysis_time = serializers.IntegerField(help_text=_("分析时长，单位为秒。只允许10、30、60"), default="10")
    ins = serializers.ListField(help_text=_("需要分析的实例列表。默认只分析proxy角色，除非指定实例"))


class SubmitBillRedisVersionUpdateInputSerializer(SubmitBillRedisBaseInputSerializer):
    node_type = serializers.ChoiceField(choices=ClusterRoleEnum.get_choices(), help_text=_("升级角色，Proxy|Backend"))
    target_version = serializers.CharField(
        help_text="目标版本，格式为：twemproxy-0.4.1-v36|predixy-1.6.1|redis-6.2.7" "|tendisplus-2.7.6-rocksdb-v8.5.3"
    )
