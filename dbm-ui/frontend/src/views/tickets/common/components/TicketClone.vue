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
  <div
    v-show="isShowTicketClone"
    class="ticket-clone-main">
    <BkButton
      class="mr-8"
      disabled
      theme="primary"
      @click="handleCancelTicket">
      {{ t('撤销单据') }}
    </BkButton>
    <BkButton
      :disabled="!isShowResubmitTicketBtn"
      @click="handleResubmitTicket">
      {{ t('再次提单') }}
    </BkButton>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    data: TicketModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();

  const ticketTypeRouteNameMap: Record<string, string> = {
    [TicketTypes.REDIS_CLUSTER_APPLY]: 'SelfServiceApplyRedis', // Redis 申请部署
    [TicketTypes.REDIS_CLUSTER_CUTOFF]: 'RedisDBReplace', // Redis 整机替换
    [TicketTypes.REDIS_PROXY_SCALE_UP]: 'RedisProxyScaleUp', // Redis 扩容接入层
    [TicketTypes.REDIS_PROXY_SCALE_DOWN]: 'RedisProxyScaleDown', // Redis 缩容接入层
    [TicketTypes.REDIS_SCALE_UPDOWN]: 'RedisCapacityChange', // Redis 集群容量变更
    [TicketTypes.REDIS_MASTER_SLAVE_SWITCH]: 'RedisMasterFailover', // Redis 主从切换
    [TicketTypes.REDIS_DATA_STRUCTURE]: 'RedisDBStructure', // Redis 定点构造
    [TicketTypes.REDIS_CLUSTER_ADD_SLAVE]: 'RedisDBCreateSlave', // Redis 重建从库
    [TicketTypes.REDIS_CLUSTER_DATA_COPY]: 'RedisDBDataCopy', // Redis 数据复制
    [TicketTypes.REDIS_CLUSTER_SHARD_NUM_UPDATE]: 'RedisClusterShardUpdate', // Redis 集群分片变更
    [TicketTypes.REDIS_CLUSTER_TYPE_UPDATE]: 'RedisClusterTypeUpdate', // Redis 集群类型变更
    [TicketTypes.REDIS_DATACOPY_CHECK_REPAIR]: 'RedisToolboxDataCheckRepair', // Redis 数据校验修复
    [TicketTypes.REDIS_CLUSTER_ROLLBACK_DATA_COPY]: 'RedisRecoverFromInstance', // Redis 以构造实例恢复
    [TicketTypes.REDIS_DATA_STRUCTURE_TASK_DELETE]: 'RedisStructureInstance', // Redis 删除构造任务
    [TicketTypes.REDIS_KEYS_EXTRACT]: 'DatabaseRedisList', // Redis 提取 Key
    [TicketTypes.REDIS_KEYS_DELETE]: 'DatabaseRedisList', // Redis 删除 key
    [TicketTypes.REDIS_BACKUP]: 'DatabaseRedisList', // Redis 集群备份
    [TicketTypes.REDIS_PURGE]: 'DatabaseRedisList', // Redis 集群清档
    [TicketTypes.REDIS_PROXY_CLOSE]: 'DatabaseRedisList', // Redis 集群禁用
    [TicketTypes.REDIS_PROXY_OPEN]: 'DatabaseRedisList', // Redis 集群启用
    [TicketTypes.REDIS_DESTROY]: 'DatabaseRedisList', // Redis 集群删除
    [TicketTypes.REDIS_PLUGIN_DNS_BIND_CLB]: 'DatabaseRedisList', // Redis 绑定CLB
    [TicketTypes.REDIS_PLUGIN_DNS_UNBIND_CLB]: 'DatabaseRedisList', // Redis 解绑CLB
    [TicketTypes.REDIS_PLUGIN_CREATE_CLB]: 'DatabaseRedisList', // Redis 创建CLB
    [TicketTypes.REDIS_PLUGIN_DELETE_CLB]: 'DatabaseRedisList', // Redis 删除CLB
    [TicketTypes.REDIS_PLUGIN_CREATE_POLARIS]: 'DatabaseRedisList', // Redis 删除构造任务
    [TicketTypes.REDIS_PLUGIN_DELETE_POLARIS]: 'DatabaseRedisList', // Redis 删除构造任务
  };

  const isShowTicketClone = computed(() => !!ticketTypeRouteNameMap[props.data.ticket_type]);
  const isShowResubmitTicketBtn = computed(() => Object.keys(props.data.details).length > 0);

  const handleResubmitTicket = async () => {
    const name = ticketTypeRouteNameMap[props.data.ticket_type];
    if (name) {
      router.push({
        name,
        query: {
          ticket_id: props.data.id,
        },
      });
    }
  };

  const handleCancelTicket = () => {
    console.log('接口未准备好');
  };
</script>
<style lang="less" scoped>
  .ticket-clone-main {
    // position: absolute;
    // bottom: 0;
    // display: flex;
    // width: 100%;
    // height: 52px;
    // padding-left: 30px;
    // background: #fff;
    // border: 1px solid #eaebf0;
    // box-shadow: inset 0 1px 0 0 #dcdee5;
    // align-items: center;
  }
</style>
