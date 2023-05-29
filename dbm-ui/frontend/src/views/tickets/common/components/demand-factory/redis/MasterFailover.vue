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
  <div class="ticket-details__info">
    <div
      class="ticket-details__item"
      style="align-items: flex-start">
      <span class="ticket-details__item-label">{{ t('需求信息') }}：</span>
      <span class="ticket-details__item-value">
        <DbOriginalTable
          :columns="columns"
          :data="tableData" />
      </span>
    </div>
  </div>
  <div class="ticket-details__info">
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('是否强制切换') }}：</span>
        <span class="ticket-details__item-value">
          {{ ticketDetails.details.force ? t('是') : t('否') }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { RedisMasterSlaveSwitchDetails } from '@services/model/ticket/details/redis';
  import TicketModel from '@services/model/ticket/ticket';

  interface Props {
    ticketDetails: TicketModel<RedisMasterSlaveSwitchDetails>
  }

  interface RowData {
    masterIp: string,
    slaveIp: string,
    clusterName: string,
    switchMode: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const columns = [
    {
      label: t('主库主机'),
      field: 'masterIp',
      showOverflowTooltip: true,
    },
    {
      label: t('所属集群'),
      field: 'clusterName',
      showOverflowTooltip: true,
    },
    {
      label: t('待切换的从库主机'),
      field: 'slaveIp',
      showOverflowTooltip: true,
    },
    {
      label: t('切换模式'),
      field: 'switchMode',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.switchMode === 'user_confirm' ? t('需人工确认') : t('无需确认')}</span>,
    },
  ];

  const tableData = computed(() => {
    const { infos, clusters } = props.ticketDetails.details;
    return infos.reduce((results, item) => {
      item.pairs.forEach((pair) => {
        const obj = {
          clusterName: clusters[item.cluster_id].immute_domain,
          masterIp: pair.redis_master,
          slaveIp: pair.redis_slave,
          switchMode: item.online_switch_type,
        };
        results.push(obj);
      });
      return results;
    }, [] as RowData[])
  });
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/ticketDetails.less';
</style>
