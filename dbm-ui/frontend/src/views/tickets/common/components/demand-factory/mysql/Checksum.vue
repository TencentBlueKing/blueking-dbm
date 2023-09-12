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
        <span class="ticket-details__item-label">{{ $t('指定执行时间') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails?.details?.timing || '--' }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ $t('自动修复') }}：</span>
        <span class="ticket-details__item-value">{{ isRepair }}</span>
      </div>
    </div>
  </div>
  <DbOriginalTable
    class="details-checksum__table"
    :columns="columns"
    :data="dataList" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type {
    MySQLChecksumDetails,
    TicketDetails,
  } from '@services/types/ticket';

  interface Props {
    ticketDetails: TicketDetails<MySQLChecksumDetails>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  type checkesumItem = {
    cluster_id: number,
    db_patterns: string[],
    ignore_dbs: string[],
    ignore_tables: string[],
    master: itemDetails,
    slaves: itemDetails[],
    table_patterns: string[],
    name: string,
  }

  type itemDetails = {
    id: number,
    ip: string,
    port: number,
  }

  // MySQL 校验
  const columns: any = [{
    label: t('目标集群'),
    field: 'name',
    showOverflowTooltip: true,
    render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
  }, {
    label: t('校验主库'),
    field: 'master',
    showOverflowTooltip: true,
    render: ({ cell }: { cell: itemDetails }) => <span>{`${cell.ip}:${cell.port}` || '--'}</span>,
  }, {
    label: t('校验从库'),
    field: 'slaves',
    showOverflowTooltip: true,
    render: ({ cell }: { cell: itemDetails[] }) => cell.map(item => <p class="pt-2 pb-2">{`${item.ip}:${item.port}` || '--'}</p>),
  }, {
    label: t('校验DB'),
    field: 'db_patterns',
    showOverflowTooltip: false,
    render: ({ cell }: { cell: string[] }) => (
      <div class="text-overflow" v-overflow-tips={{
          content: cell,
        }}>
        {cell.map(item => <bk-tag>{item}</bk-tag>)}
      </div>
    ),
  }, {
    label: t('忽略DB'),
    field: 'ignore_dbs',
    showOverflowTooltip: false,
    render: ({ cell }: { cell: string[] }) => (
      <div class="text-overflow" v-overflow-tips={{
          content: cell,
        }}>
        {cell.length > 0 ? cell.map(item => <bk-tag>{item}</bk-tag>) : '--'}
      </div>
    ),
  }, {
    label: t('校验表名'),
    field: 'table_patterns',
    showOverflowTooltip: false,
    render: ({ cell }: { cell: string[] }) => (
      <div class="text-overflow" v-overflow-tips={{
          content: cell,
        }}>
        {cell.map(item => <bk-tag>{item}</bk-tag>)}
      </div>
    ),
  }, {
    label: t('忽略表名'),
    field: 'ignore_tables',
    showOverflowTooltip: false,
    render: ({ cell }: { cell: string[] }) => (
      <div class="text-overflow" v-overflow-tips={{
          content: cell,
        }}>
        {cell.length > 0 ? cell.map(item => <bk-tag>{item}</bk-tag>) : '--'}
      </div>
    ),
  }];

  // 修复数据
  const isRepair = computed(() => (props.ticketDetails?.details?.data_repair.is_repair ? t('是') : t('否')));

  const dataList = computed(() => {
    const list: checkesumItem[] = [];
    const infosData = props.ticketDetails?.details?.infos || [];
    const clusters = props.ticketDetails?.details?.clusters || {};
    infosData.forEach((item) => {
      const clusterName = clusters[item.cluster_id]?.name;
      list.push(Object.assign({
        cluster_id: item.cluster_id,
        db_patterns: item.db_patterns,
        ignore_dbs: item.ignore_dbs,
        ignore_tables: item.ignore_tables,
        master: item.master,
        slaves: item.slaves,
        table_patterns: item.table_patterns,
        name: clusterName,
      }));
    });
    return list;
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

.details-checksum {
  &__table {
    padding-left: 80px;
  }
}
</style>
