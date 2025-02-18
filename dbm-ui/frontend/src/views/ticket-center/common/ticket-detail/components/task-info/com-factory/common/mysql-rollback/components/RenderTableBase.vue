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
  <BkTable :data="ticketDetails.details.infos">
    <BkTableColumn
      :label="t('集群')"
      :min-width="220">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <slot />
    <BkTableColumn
      :label="t('备份源')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{ backupSourceMap[data.backup_source as keyof typeof backupSourceMap] }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('回档类型')">
      <template #default="{ data }: { data: RowData }">
        <span v-if="data.rollback_time">{{ t('回档到指定时间') }} - {{ utcDisplayTime(data.rollback_time) }}</span>
        <span v-else-if="data.backupinfo.backup_time && data.backupinfo.mysql_role">
          {{ t('备份记录') }} - {{ data.backupinfo?.mysql_role }}
          {{ utcDisplayTime(data.backupinfo?.backup_time) }}
        </span>
        <span v-else>--</span>
      </template>
    </BkTableColumn>
    <template v-if="showDbName">
      <BkTableColumn :label="t('回档DB名')">
        <template #default="{ data }: { data: RowData }">
          <TagBlock :data="data.databases" />
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('忽略DB名')">
        <template #default="{ data }: { data: RowData }">
          <TagBlock :data="data.databases_ignore" />
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('回档表名')">
        <template #default="{ data }: { data: RowData }">
          <TagBlock :data="data.tables" />
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('忽略表名')">
        <template #default="{ data }: { data: RowData }">
          <TagBlock :data="data.tables_ignore" />
        </template>
      </BkTableColumn>
    </template>
  </BkTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import TagBlock from '@components/tag-block/Index.vue';

  import { utcDisplayTime } from '@utils';

  interface Props {
    ticketDetails: TicketModel<Mysql.RollbackCluster>;
    showDbName?: boolean;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  withDefaults(defineProps<Props>(), {
    showDbName: true,
  });

  const { t } = useI18n();

  const backupSourceMap = {
    remote: t('远程备份'),
    local: t('本地备份'),
  };
</script>
