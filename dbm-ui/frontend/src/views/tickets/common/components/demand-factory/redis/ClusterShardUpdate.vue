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
    class="ticket-details-item"
    style="align-items: flex-start">
    <span class="ticket-details-item-label">{{ t('变更信息') }}：</span>
    <span class="ticket-details-item-value">
      <BkLoading :loading="loading">
        <DbOriginalTable
          :columns="columns"
          :data="tableData" />
      </BkLoading>
    </span>
  </div>

  <div class="ticket-details-list">
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('校验与修复类型') }}：</span>
      <span class="ticket-details-item-value">
        {{ repairAndVerifyTypesMap[ticketDetails.details.data_check_repair_setting.type] }}
      </span>
    </div>
    <div
      v-if="ticketDetails.details.data_check_repair_setting.type !== 'no_check_no_repair'"
      class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('校验与修复类型') }}：</span>
      <span class="ticket-details-item-value">
        {{ repairAndVerifyFrequencyMap[ticketDetails.details.data_check_repair_setting.execution_frequency] }}
      </span>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RedisModel from '@services/model/redis/redis';
  import type { RedisClusterShardUpdateDetails } from '@services/model/ticket/details/redis';
  import TicketModel from '@services/model/ticket/ticket';
  import { getRedisListByBizId } from '@services/source/redis';

  import { repairAndVerifyFrequencyList, repairAndVerifyTypeList } from '@views/db-manage/redis/common/const';

  interface Props {
    ticketDetails: TicketModel<RedisClusterShardUpdateDetails>
  }

  interface RowData {
    deployPlan: string,
    capacity: number,
    futureCapacity: number,
    dbVersion: string,
    switchMode: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = ref<RowData[]>([]);

  const { infos } = props.ticketDetails.details;

  const columns = [
    {
      label: t('源集群'),
      field: 'clusterName',
      showOverflowTooltip: true,
    },
    {
      label: t('架构版本'),
      field: 'clusterTypeName',
      showOverflowTooltip: true,
    },
    {
      label: t('当前集群容量/QPS'),
      field: 'currentSepc',
      showOverflowTooltip: true,
    },
    {
      label: t('当前容量需求'),
      field: 'capacity',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.capacity}G</span>,
    },
    {
      label: t('未来容量需求'),
      field: 'futureCapacity',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.futureCapacity}G</span>,
    },
    {
      label: t('部署方案'),
      field: 'deployPlan',
      showOverflowTooltip: true,
    },
    {
      label: t('版本'),
      field: 'dbVersion',
      showOverflowTooltip: true,
    },
    {
      label: t('切换模式'),
      field: 'switchMode',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.switchMode === 'user_confirm' ? t('需人工确认') : t('无需确认')}</span>,
    },
  ];

  const repairAndVerifyTypesMap = generateMap(repairAndVerifyTypeList);

  const repairAndVerifyFrequencyMap = generateMap(repairAndVerifyFrequencyList);

  const { loading } = useRequest(getRedisListByBizId, {
    defaultParams: [{
      bk_biz_id: props.ticketDetails.bk_biz_id,
      offset: 0,
      limit: -1,
    }],
    onSuccess: async (result) => {
      if (result.results.length < 1) {
        return;
      }

      const clusterMap = result.results.reduce((obj, item) => {
        Object.assign(obj, { [item.id]: item });
        return obj;
      }, {} as Record<string, RedisModel>);
      tableData.value = infos.map((item) => {
        const currentCluster = clusterMap[item.src_cluster];
        const specConfig = currentCluster.cluster_spec;
        return ({
          clusterName: currentCluster.master_domain,
          clusterType: currentCluster.cluster_spec.spec_cluster_type,
          clusterTypeName: currentCluster.cluster_type_name,
          currentSepc: `${currentCluster.cluster_capacity}G_${specConfig.qps.max}/s（${item.current_shard_num} 分片）`,
          deployPlan: `${item.cluster_shard_num} 分片`,
          dbVersion: item.db_version,
          switchMode: item.online_switch_type,
          capacity: item.capacity,
          futureCapacity: item.future_capacity,
        });
      });
    },
  });

  // 生成映射表
  function generateMap(arr: { label: string, value: string}[]) {
    return arr.reduce((obj, item) => {
      Object.assign(obj, { [item.value]: item.label });
      return obj;
    }, {} as Record<string, string>);
  }
</script>
<style lang="less" scoped>
  @import '@views/tickets/common/styles/ticketDetails.less';
</style>
