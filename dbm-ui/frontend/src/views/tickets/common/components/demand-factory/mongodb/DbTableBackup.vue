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
  <div class="ticket-details__info">
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('备份文件保存时间') }}：</span>
        <span class="ticket-details__item-value">{{ fileTag === 'normal_backup' ? t('常规备份（25天）') : t('长期备份（3年）') }}</span>
      </div>
      <div v-if="backupType" class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('备份位置') }}：</span>
        <span class="ticket-details__item-value">{{ backupType }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { TicketDetails } from '@services/types/ticket';

  interface DbTableBackupDetails {
    clusters: {
      [clusterId: string]: {
        alias: string;
        bk_biz_id: number;
        bk_cloud_id: number;
        cluster_type: string;
        cluster_type_name: string;
        creator: string;
        db_module_id: number;
        disaster_tolerance_level: string;
        id: number;
        immute_domain: string;
        major_version: string;
        name: string;
        phase: string;
        region: string;
        status: string;
        tag: {
          bk_biz_id?: number;
          name?: string;
          type?: string;
        }[];
        time_zone: string;
        updater: string;
      };
    };
    file_tag: string;
    backup_type?: string;
    infos: {
      cluster_ids: number[];
      backup_host: string;
      ns_filter: {
        db_patterns: string[];
        ignore_dbs: string[];
        ignore_tables: string[];
        table_patterns: string[];
      };
    }[];
  }

  interface Props {
    ticketDetails: TicketDetails<DbTableBackupDetails>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const {
    clusters,
    backup_type: backupType,
    file_tag: fileTag,
    infos,
  } = props.ticketDetails.details;

  const isShowBackupHost = infos[0].backup_host;

  const columns = [
    {
      label: backupType ? t('目标分片集群') : t('目标副本集集群'),
      field: 'immute_domain',
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
    }];

  if (isShowBackupHost) {
    columns.splice(1, 0, {
      label: t('目标主机'),
      field: 'backup_host',
    });
  }

  const dataList =  infos.map(item => ({
    immute_domain: item.cluster_ids.map(id => clusters[id].immute_domain).join(','),
    backup_host: item.backup_host,
    db_patterns: item.ns_filter.db_patterns,
    ignore_dbs: item.ns_filter.ignore_dbs,
    ignore_tables: item.ns_filter.ignore_tables,
    table_patterns: item.ns_filter.table_patterns,
  }));
</script>

<style lang="less" scoped>
@import "@views/tickets/common/styles/DetailsTable.less";
@import "@views/tickets/common/styles/ticketDetails.less";

.ticket-details {
  &__info {
    padding-left: 80px;
  }

  &__item {
    &-label {
      min-width: 0;
      text-align: left;
    }
  }
}

.details-backup {
  &__table {
    padding-left: 80px;
  }
}
</style>
