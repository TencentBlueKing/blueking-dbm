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
      style="align-items: flex-start;">
      <span
        class="ticket-details__item-label">{{ t('需求信息') }}：</span>
      <span class="ticket-details__item-value">
        <BkLoading :loading="loading">
          <DbOriginalTable
            :columns="columns"
            :data="tableData" />
        </BkLoading>
      </span>
    </div>
  </div>

  <div class="ticket-details__info">
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('只启用只读集群') }}：</span>
        <span class="ticket-details__item-value">
          {{ ticketDetails.details.is_only_add_slave_domain ? t('是') : t('否') }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getList } from '@services/spider';
  import type { SpiderEnableDetails, TicketDetails } from '@services/types/ticket';

  interface Props {
    ticketDetails: TicketDetails<SpiderEnableDetails>
  }

  interface RowData {
    clusterName: string
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  // eslint-disable-next-line vue/no-setup-props-destructure
  const list = props.ticketDetails.details.cluster_ids;
  const tableData = ref<RowData[]>([]);
  const columns = [
    {
      label: t('集群'),
      field: 'clusterName',
      showOverflowTooltip: true,
    },
  ];

  const { loading } = useRequest(getList, {
    onSuccess: (r) => {
      if (r.results.length < 1) {
        return;
      }
      const clusterMap = r.results.reduce((obj, item) => {
        Object.assign(obj, { [item.id]: item.master_domain  });
        return obj;
      }, {} as Record<number, string>);

      tableData.value = list.reduce((results, clusterId) => {
        const obj = {
          clusterName: clusterMap[clusterId],
        };
        results.push(obj);
        return results;
      }, [] as RowData[]);
    },
  });

</script>
<style lang="less" scoped>
  @import "@views/tickets/common/styles/ticketDetails.less";
</style>
