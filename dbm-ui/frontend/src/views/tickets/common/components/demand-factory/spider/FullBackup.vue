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
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('备份类型') }}：</span>
        <span class="ticket-details__item-value">{{ infos.backup_type === 'physical' ? $t('物理备份') : $t('逻辑备份') }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('备份保存时间') }}：</span>
        <span class="ticket-details__item-value">
          {{ infos.file_tag === 'LONGDAY_DBFILE_3Y' ? $t('3年') : $t('30天') }}
        </span>
      </div>
    </div>
  </div>
  <BkLoading :loading="loading">
    <DbOriginalTable
      :columns="columns"
      :data="tableData" />
  </BkLoading>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getList } from '@services/spider';
  import type { SpiderFullBackupDetails, TicketDetails } from '@services/types/ticket';

  interface Props {
    ticketDetails: TicketDetails<SpiderFullBackupDetails>
  }

  interface RowData {
    clusterName: string,
    position: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  // eslint-disable-next-line vue/no-setup-props-destructure
  const { infos } = props.ticketDetails.details;
  const tableData = ref<RowData[]>([]);
  const columns = [
    {
      label: t('目标集群'),
      field: 'clusterName',
    },
    {
      label: t('备份位置'),
      field: 'position',
    },
  ];

  const { loading } = useRequest(getList, {
    onSuccess: (r) => {
      if (r.results.length < 1) {
        return;
      }
      const clusterMap = r.results.reduce((obj, item) => {
        Object.assign(obj, { [item.id]: item.master_domain });
        return obj;
      }, {} as Record<number, string>);

      tableData.value = infos.clusters.reduce((results, item) => {
        const obj = {
          clusterName: clusterMap[item.id],
          position: item.backup_local,
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
