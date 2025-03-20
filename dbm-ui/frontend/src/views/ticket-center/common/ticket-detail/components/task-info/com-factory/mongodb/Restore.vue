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
  <template v-if="tableSettingData.length > 0">
    <div class="ticket-details-list">
      <div class="ticket-details-item">
        <span class="ticket-details-item-label">{{ t('库表设置') }}：</span>
      </div>
    </div>
    <DbOriginalTable
      class="details-backup__table"
      :columns="dbTableColumns"
      :data="tableSettingData" />
  </template>
  <div class="ticket-details-list">
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('构造新主机规格') }}：</span>
      <span class="ticket-details-item-value">
        {{ specs[resource_spec.mongodb.spec_id].name ?? '--' }}
      </span>
    </div>
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('每台主机构造Shard数量') }}：</span>
      <span class="ticket-details-item-value">
        {{ instance_per_host }}
      </span>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import { utcDisplayTime } from '@utils';

  interface Props {
    ticketDetails: TicketModel<Mongodb.Restore>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_RESTORE,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const {
    backupinfo,
    cluster_ids: clusterIds,
    clusters,
    instance_per_host,
    ns_filter: nsFilter,
    resource_spec,
    rollback_time: rollbackTime,
    specs,
  } = props.ticketDetails.details;

  const columns = [
    {
      field: 'immute_domain',
      label: t('集群'),
      showOverflowTooltip: true,
    },
    {
      field: 'struct_type',
      label: t('构造类型'),
      rowspan: clusterIds.length,
      showOverflowTooltip: true,
    },
    {
      field: 'backup_file',
      label: t('备份文件'),
    },
  ];

  if (!backupinfo) {
    columns[2] = {
      field: 'target_time',
      label: t('指定时间'),
    };
  }

  const dbTableColumns = [
    {
      field: 'db_patterns',
      label: t('备份DB名'),
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

  const tableSettingData = nsFilter
    ? [
        {
          ...nsFilter,
        },
      ]
    : [];

  const tableData = computed(() =>
    clusterIds.map((id) => ({
      backup_file: backupinfo
        ? `${clusters[id].cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER ? backupinfo[id].set_name : ''}-${backupinfo[id].role_type}-${utcDisplayTime(backupinfo[id].end_time)}`
        : '',
      immute_domain: clusters[id].immute_domain,
      struct_type: backupinfo ? t('备份记录') : t('回档至指定时间'),
      target_time: rollbackTime ? utcDisplayTime(rollbackTime) : '',
    })),
  );
</script>
