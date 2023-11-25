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
        <span class="ticket-details__item-label">{{ $t('所属业务') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.bk_biz_name || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('备份选项') }}：</span>
        <span class="ticket-details__item-value">{{ backupOptions }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('备份类型') }}：</span>
        <span class="ticket-details__item-value">{{ backupType }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('备份保存时间') }}：</span>
        <span class="ticket-details__item-value">{{ backupTime }}</span>
      </div>
    </div>
  </div>
  <DbOriginalTable
    class="details-backup__table"
    :columns="columns"
    :data="dataList" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type {
    MySQLFullBackupDetails,
    TicketDetails,
  } from '@services/types/ticket';

  interface Props {
    ticketDetails: TicketDetails<MySQLFullBackupDetails>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  type fullBackupItem = {
    immute_domain: string,
    backup_local: string,
    name: string,
    cluster_id:number,
  }

  // MySQL 全库备份
  const columns = [
    {
      label: t('集群ID'),
      field: 'cluster_id',
      render: ({ cell }: { cell: number }) => <span>{cell || '--'}</span>,
    },
    {
      label: t('集群名称'),
      field: 'immute_domain',
      showOverflowTooltip: false,
      render: ({ data }: { data: fullBackupItem }) => (
      <div class="cluster-name text-overflow"
        v-overflow-tips={{
          content: `
            <p>${t('域名')}：${data.immute_domain}</p>
            ${data.name ? `<p>${('集群别名')}：${data.name}</p>` : null}
          `,
          allowHTML: true,
      }}>
        <span>{data.immute_domain}</span><br />
        <span class="cluster-name__alias">{data.name}</span>
      </div>
    ),
    },
    {
      label: t('备份位置'),
      field: 'backup_local',
      render: ({ cell }: { cell: number }) => <span>{cell || '--'}</span>,
    },
  ];

  const dataList = computed(() => {
    const infosData = props.ticketDetails?.details?.infos || {};
    const clusters = props.ticketDetails?.details?.clusters || {};
    return infosData?.clusters?.reduce((results, item) => {
      const clusterData = clusters[item.cluster_id];
      results.push(Object.assign({
        immute_domain: clusterData?.immute_domain,
        name: clusterData?.name,
        backup_local: item.backup_local,
        cluster_id: item.cluster_id,
      }));
      return results;
    }, [] as fullBackupItem[]);
  });

  // 备份选项
  const backupOptions = computed(() => {
    if (props.ticketDetails?.details?.infos?.online) {
      return t('在线备份');
    }
    return t('停机备份');
  });

  // 备份类型
  const backupType = computed(() => {
    if (props.ticketDetails?.details?.infos?.backup_type === 'logical') {
      return t('逻辑备份');
    }
    return '--';
  });

  // 备份保存时间
  const backupTime = computed(() => {
    if (props.ticketDetails?.details?.infos?.file_tag === 'MYSQL_FULL_BACKUP') {
      return t('30天');
    }
    return t('3年');
  });
</script>

<style lang="less" scoped>
@import "@views/tickets/common/styles/DetailsTable.less";
@import "@views/tickets/common/styles/ticketDetails.less";

.ticket-details {
  &__info {
    padding-left: 0;
  }

  &__item {
    &-label {
      min-width: 140px;
    }
  }
}

.details-backup {
  &__table {
    padding-left: 80px;
  }
}
</style>
