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
    :data="dataList" />
  <div class="ticket-details-list">
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('备份保存时间') }}：</span>
      <span class="ticket-details-item-value">{{ fileTagText }}</span>
    </div>
    <div
      v-if="backupType"
      class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('备份位置') }}：</span>
      <span class="ticket-details-item-value">{{ backupType }}</span>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mongodb.Backup>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_BACKUP,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { backup_type: backupType, clusters, file_tag: fileTag, infos } = props.ticketDetails.details;

  const isShowBackupHost = infos[0].backup_host;

  const columns = [
    {
      field: 'immute_domain',
      label: backupType ? t('目标分片集群') : t('目标副本集集群'),
    },
    {
      field: 'db_patterns',
      label: t('备份DB名'),
      render: ({ cell }: { cell: string[] }) => (
        <div
          v-overflow-tips={{
            content: cell,
          }}
          class='text-overflow'>
          {cell.map((item) => (
            <bk-tag>{item}</bk-tag>
          ))}
        </div>
      ),
      showOverflowTooltip: false,
    },
    {
      field: 'ignore_dbs',
      label: t('忽略DB名'),
      render: ({ cell }: { cell: string[] }) => (
        <div
          v-overflow-tips={{
            content: cell,
          }}
          class='text-overflow'>
          {cell.length > 0 ? cell.map((item) => <bk-tag>{item}</bk-tag>) : '--'}
        </div>
      ),
      showOverflowTooltip: false,
    },
    {
      field: 'table_patterns',
      label: t('备份表名'),
      render: ({ cell }: { cell: string[] }) => (
        <div
          v-overflow-tips={{
            content: cell,
          }}
          class='text-overflow'>
          {cell.map((item) => (
            <bk-tag>{item}</bk-tag>
          ))}
        </div>
      ),
      showOverflowTooltip: false,
    },
    {
      field: 'ignore_tables',
      label: t('忽略表名'),
      render: ({ cell }: { cell: string[] }) => (
        <div
          v-overflow-tips={{
            content: cell,
          }}
          class='text-overflow'>
          {cell.length > 0 ? cell.map((item) => <bk-tag>{item}</bk-tag>) : '--'}
        </div>
      ),
      showOverflowTooltip: false,
    },
  ];

  if (isShowBackupHost) {
    columns.splice(1, 0, {
      field: 'backup_host',
      label: t('目标主机'),
    });
  }

  const dataList = infos.map((item) => ({
    backup_host: item.backup_host,
    db_patterns: item.ns_filter.db_patterns,
    ignore_dbs: item.ns_filter.ignore_dbs,
    ignore_tables: item.ns_filter.ignore_tables,
    immute_domain: item.cluster_ids.map((id) => clusters[id].immute_domain).join(','),
    table_patterns: item.ns_filter.table_patterns,
  }));

  const fileTagMap: Record<string, string> = {
    a_year_backup: t('1年'),
    forever_backup: t('3年'),
    half_year_backup: t('6个月'),
    normal_backup: t('25天'),
  };

  const fileTagText = fileTagMap[fileTag];
</script>
