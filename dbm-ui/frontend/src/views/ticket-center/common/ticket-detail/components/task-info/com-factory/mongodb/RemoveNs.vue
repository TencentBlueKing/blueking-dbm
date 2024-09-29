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
  <DbOriginalTable
    class="details-backup__table"
    :columns="columns"
    :data="tableData" />
  <div class="ticket-details-list">
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('忽略业务连接') }}：</span>
      <span class="ticket-details-item-value">
        {{ ticketDetails.details.is_safe ? t('否') : t('是') }}
      </span>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mongodb.RemoveNs>
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.MONGODB_REMOVE_NS,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const {
    clusters,
    infos,
  } = props.ticketDetails.details;
  const columns = [
    {
      label: t('目标集群'),
      field: 'immute_domain',
      showOverflowTooltip: true,
    },
    {
      label: t('清档类型'),
      field: 'drop_type',
      showOverflowTooltip: true,
      render: ({ cell }: { cell: string }) => (
        <span>
          {cell === 'drop_collection' ? t('直接删除表') : t('将表暂时重命名，用于需要快速恢复的情况')}
        </span>
      ),
    },
    {
      label: t('是否删除索引'),
      field: 'drop_index',
      render: ({ cell }: { cell: boolean }) => (
        <span>
          {cell ? t('是') : t('否')}
        </span>
      ),
    },
    {
      label: t('备份DB名'),
      field: 'db_patterns',
      showOverflowTooltip: false,
      render: ({ cell }: { cell: string[] }) => (
        <div class="text-overflow" v-overflow-tips={{
            content: cell,
          }}>
          {cell.map(item => <bk-tag>{item}</bk-tag>)}
        </div>
      ),
    },
    {
      label: t('忽略DB名'),
      field: 'ignore_dbs',
      showOverflowTooltip: false,
      render: ({ cell }: { cell: string[] }) => (
        <div class="text-overflow" v-overflow-tips={{
            content: cell,
          }}>
          {cell.length > 0 ? cell.map(item => <bk-tag>{item}</bk-tag>) : '--'}
        </div>
      ),
    },
    {
      label: t('备份表名'),
      field: 'table_patterns',
      showOverflowTooltip: false,
      render: ({ cell }: { cell: string[] }) => (
        <div class="text-overflow" v-overflow-tips={{
            content: cell,
          }}>
          {cell.map(item => <bk-tag>{item}</bk-tag>)}
        </div>
      ),
    },
    {
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
    },
  ];

  const tableData = infos.map(item => ({
    immute_domain: item.cluster_ids.map(id => clusters[id].immute_domain).join(','),
    drop_type: item.drop_type,
    drop_index: item.drop_index,
    ...item.ns_filter,
  }));
</script>
