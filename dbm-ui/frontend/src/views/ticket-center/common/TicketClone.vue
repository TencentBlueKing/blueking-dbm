<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <span
    v-bk-tooltips="{
      content: t('暂不支持'),
      disabled: isSupported,
    }">
    <BkButton
      :disabled="!isSupported"
      text
      theme="primary"
      v-bind="attrs"
      @click="handleResubmitTicket">
      {{ t('再次提单') }}
    </BkButton>
  </span>
</template>
<script setup lang="ts">
  import { useAttrs } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import { getBusinessHref } from '@utils';

  interface Props {
    data: TicketModel<unknown>;
  }

  const props = defineProps<Props>();

  const attrs = useAttrs();
  const { t } = useI18n();
  const router = useRouter();

  const allRouteNames = new Set(router.getRoutes().map((route) => route.name as string));

  const ticketTypesMap = Object.fromEntries(Object.entries(TicketTypes).filter(([key]) => allRouteNames.has(key)));

  const ticketTypeRouteNameMap: Record<string, string> = {
    ...ticketTypesMap,
    [TicketTypes.DORIS_APPLY]: 'DorisApply',
    [TicketTypes.ES_APPLY]: 'EsApply',
    [TicketTypes.ES_CREATE_CLB]: 'EsList', // es 启用clb',
    [TicketTypes.ES_CREATE_POLARIS]: 'EsList', // es 启用北极星',
    [TicketTypes.ES_DNS_BIND_CLB]: 'EsList', // es 主域名指向CLB ip
    [TicketTypes.ES_DNS_UNBIND_CLB]: 'EsList', // es 解绑主域名指向clb
    [TicketTypes.HDFS_APPLY]: 'HdfsApply',
    [TicketTypes.INFLUXDB_APPLY]: 'SelfServiceApplyInfluxDB',
    [TicketTypes.KAFKA_APPLY]: 'KafkaApply',
    [TicketTypes.MONGODB_REPLICASET_APPLY]: 'MongoDBReplicaSetApply',
    [TicketTypes.MONGODB_SHARD_APPLY]: 'MongoDBSharedClusterApply',
    [TicketTypes.MYSQL_ADD_CLB]: 'DatabaseTendbha', // mysql 启用clb',
    [TicketTypes.MYSQL_AUTHORIZE_RULES]: 'PermissionRules', // Mysql 授权
    [TicketTypes.MYSQL_CLB_BIND_DOMAIN]: 'DatabaseTendbha', // mysql 主域名指向CLB ip
    [TicketTypes.MYSQL_CLB_UNBIND_DOMAIN]: 'DatabaseTendbha', // mysql 解绑主域名指向clb
    [TicketTypes.MYSQL_EXCEL_AUTHORIZE_RULES]: '', // Mysql excel 授权
    [TicketTypes.MYSQL_HA_APPLY]: 'SelfServiceApplyHa', // Mysql 主从部署
    [TicketTypes.MYSQL_HA_DESTROY]: 'DatabaseTendbha', // Mysql 删除
    [TicketTypes.MYSQL_HA_DISABLE]: 'DatabaseTendbha', // Mysql 禁用
    [TicketTypes.MYSQL_HA_ENABLE]: 'DatabaseTendbha', // Mysql 启用
    [TicketTypes.MYSQL_SINGLE_APPLY]: 'SelfServiceApplySingle', // Mysql 单节点部署
    [TicketTypes.MYSQL_SINGLE_DESTROY]: 'DatabaseTendbsingle', // Mysql 单节点删除
    [TicketTypes.MYSQL_SINGLE_DISABLE]: 'DatabaseTendbsingle', // Mysql 单节点禁用
    [TicketTypes.MYSQL_SINGLE_ENABLE]: 'DatabaseTendbsingle', // Mysql 单节点启用
    [TicketTypes.PULSAR_APPLY]: 'PulsarApply',
    [TicketTypes.REDIS_CLUSTER_APPLY]: 'SelfServiceApplyRedis', // Redis 申请部署
    [TicketTypes.REDIS_DATA_STRUCTURE_TASK_DELETE]: 'RedisStructureInstance', // Redis 删除构造任务
    [TicketTypes.REDIS_DESTROY]: 'DatabaseRedisList', // Redis 集群删除
    [TicketTypes.REDIS_INS_APPLY]: 'SelfServiceApplyRedisHa',
    [TicketTypes.REDIS_PLUGIN_CREATE_CLB]: 'DatabaseRedisList', // Redis 创建CLB
    [TicketTypes.REDIS_PLUGIN_CREATE_POLARIS]: 'DatabaseRedisList', // Redis 删除构造任务
    [TicketTypes.REDIS_PLUGIN_DELETE_CLB]: 'DatabaseRedisList', // Redis 删除CLB
    [TicketTypes.REDIS_PLUGIN_DELETE_POLARIS]: 'DatabaseRedisList', // Redis 删除构造任务
    [TicketTypes.REDIS_PLUGIN_DNS_BIND_CLB]: 'DatabaseRedisList', // Redis 绑定CLB
    [TicketTypes.REDIS_PLUGIN_DNS_UNBIND_CLB]: 'DatabaseRedisList', // Redis 解绑CLB
    [TicketTypes.REDIS_PROXY_CLOSE]: 'DatabaseRedisList', // Redis 集群禁用
    [TicketTypes.REDIS_PROXY_OPEN]: 'DatabaseRedisList', // Redis 集群启用
    [TicketTypes.RIAK_CLUSTER_APPLY]: 'RiakApply',
    [TicketTypes.SQLSERVER_DATA_MIGRATE]: 'sqlServerDataMigrate', // sqlserver 数据迁移
    [TicketTypes.SQLSERVER_HA_APPLY]: 'SqlServiceHaApply',
    [TicketTypes.SQLSERVER_SINGLE_APPLY]: 'SqlServiceSingleApply',
    [TicketTypes.TENDBCLUSTER_ADD_CLB]: 'tendbClusterList', // tendbcluster 启用clb
    [TicketTypes.TENDBCLUSTER_APPLY]: 'spiderApply', // spider 集群部署
    [TicketTypes.TENDBCLUSTER_AUTHORIZE_RULES]: 'spiderPermission',
    [TicketTypes.TENDBCLUSTER_CLB_BIND_DOMAIN]: 'tendbClusterList', // tendbcluster 主域名指向CLB ip
    [TicketTypes.TENDBCLUSTER_CLB_UNBIND_DOMAIN]: 'tendbClusterList', // tendbcluster 解绑主域名指向clb
  };

  const isSupported = computed(() => !!ticketTypeRouteNameMap[props.data.ticket_type]);

  const handleResubmitTicket = async () => {
    // let name = '';
    // if (
    //   [
    //     TicketTypes.REDIS_BACKUP,
    //     TicketTypes.REDIS_KEYS_DELETE,
    //     TicketTypes.REDIS_KEYS_EXTRACT,
    //     TicketTypes.REDIS_PURGE,
    //   ].includes(props.data.ticket_type)
    // ) {
    //   const clusterInfo = Object.values((props.data.details as Redis.ClusterRollbackDataCopy).clusters)[0];
    //   if (clusterInfo.cluster_type === ClusterTypes.REDIS_INSTANCE) {
    //     name = 'DatabaseRedisHaList';
    //   } else {
    //     name = 'DatabaseRedisList';
    //   }
    // } else {
    //   name = ticketTypeRouteNameMap[props.data.ticket_type];
    // }

    const name = ticketTypeRouteNameMap[props.data.ticket_type];
    if (name) {
      const { href } = router.resolve({
        name,
        query: {
          ticketId: props.data.id,
          ticketType: props.data.ticket_type,
        },
      });
      window.open(getBusinessHref(href, props.data.bk_biz_id), '_blank');
    }
  };
</script>
