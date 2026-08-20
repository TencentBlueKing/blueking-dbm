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
  <TicketInfoTable
    :data="tableData"
    row-key="immute_domain">
    <TicketInfoTableColumn
      col-key="immute_domain"
      :get-copy-value="(row: RowData) => row.immute_domain"
      :title="t('集群')" />
    <TicketInfoTableColumn
      col-key="struct_type"
      :title="t('构造类型')" />
    <TicketInfoTableColumn
      v-if="backupinfo"
      col-key="backup_file"
      :title="t('备份文件')" />
    <TicketInfoTableColumn
      v-else
      col-key="target_time"
      :title="t('指定时间')" />
  </TicketInfoTable>
  <template v-if="tableSettingData.length > 0">
    <div class="ticket-details-list">
      <div class="ticket-details-item">
        <span class="ticket-details-item-title">{{ t('库表设置') }}：</span>
      </div>
    </div>
    <TicketInfoTable
      :data="tableSettingData"
      row-key="db_patterns">
      <TicketInfoTableColumn
        col-key="db_patterns"
        :title="t('备份DB名')">
        <template #default="{ row }">
          <div
            v-overflow-tips="{ content: row.db_patterns }"
            class="text-overflow">
            <template v-if="row.db_patterns.length > 0">
              <DbTag
                v-for="(item, index) in row.db_patterns"
                :key="index">
                {{ item }}
              </DbTag>
            </template>
            <span v-else> -- </span>
          </div>
        </template>
      </TicketInfoTableColumn>
      <TicketInfoTableColumn
        col-key="ignore_dbs"
        :title="t('备份DB名')">
        <template #default="{ row }">
          <div
            v-overflow-tips="{ content: row.ignore_dbs }"
            class="text-overflow">
            <template v-if="row.ignore_dbs.length > 0">
              <DbTag
                v-for="(item, index) in row.ignore_dbs"
                :key="index">
                {{ item }}
              </DbTag>
            </template>
            <span v-else> -- </span>
          </div>
        </template>
      </TicketInfoTableColumn>
      <TicketInfoTableColumn
        col-key="table_patterns"
        :title="t('备份表名')">
        <template #default="{ row }">
          <div
            v-overflow-tips="{ content: row.table_patterns }"
            class="text-overflow">
            <template v-if="row.table_patterns.length > 0">
              <DbTag
                v-for="(item, index) in row.table_patterns"
                :key="index">
                {{ item }}
              </DbTag>
            </template>
            <span v-else> -- </span>
          </div>
        </template>
      </TicketInfoTableColumn>
      <TicketInfoTableColumn
        col-key="ignore_tables"
        :title="t('忽略表名')">
        <template #default="{ row }">
          <div
            v-overflow-tips="{ content: row.ignore_tables }"
            class="text-overflow">
            <template v-if="row.ignore_tables.length > 0">
              <DbTag
                v-for="(item, index) in row.ignore_tables"
                :key="index">
                {{ item }}
              </DbTag>
            </template>
            <span v-else> -- </span>
          </div>
        </template>
      </TicketInfoTableColumn>
    </TicketInfoTable>
  </template>
  <div class="ticket-details-list">
    <div class="ticket-details-item">
      <span class="ticket-details-item-title">{{ t('构造新主机规格') }}：</span>
      <span class="ticket-details-item-value">
        {{ specs[resource_spec.mongodb.spec_id].name ?? '--' }}
      </span>
    </div>
    <div class="ticket-details-item">
      <span class="ticket-details-item-title">{{ t('每台主机构造Shard数量') }}：</span>
      <span class="ticket-details-item-value">
        {{ instance_per_host }}
      </span>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import { utcDisplayTime } from '@utils';

  interface Props {
    ticketDetails: TicketModel<Mongodb.Restore>;
  }

  type RowData = UnwrapRef<typeof tableData>[number];

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
