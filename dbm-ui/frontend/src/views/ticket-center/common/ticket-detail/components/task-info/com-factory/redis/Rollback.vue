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
    :data="ticketDetails.details.infos"
    row-key="cluster_id">
    <TicketInfoTableColumn
      col-key="cluster_id"
      :get-copy-value="(row: RowData) => ticketDetails.details.clusters[row.cluster_id].immute_domain"
      :min-width="180"
      :title="t('待构造的集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="cluster_type_name"
      :title="t('架构类型')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].cluster_type_name }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="backup_record"
      :min-width="240"
      :title="t('备份记录')">
      <template #default="{ row }: { row: RowData }">
        <p>{{ row.backup_identify }}</p>
        <p>{{ getBackupTypeText(row.backup_identify) }}</p>
        <p>{{ t('构造范围') }}：{{ getScopeDisplay(row) }}</p>
        <p v-if="hasBinlog(ticketDetails.details.clusters[row.cluster_id].cluster_type)">
          {{ t('构造到') }}：{{ row.recovery_time_point ? utcDisplayTime(row.recovery_time_point) : t('仅用全备') }}
        </p>
        <p v-if="row.allow_binlog_nonconsecutive">{{ t('binlog 不连续') }}：{{ t('仍构造') }}</p>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="count"
      :title="t('构造主机数量')">
      <template #default="{ row }: { row: RowData }">
        {{ row.resource_spec.redis.count }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="spec"
      :title="t('目标规格')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.specs[row.resource_spec.redis.spec_id].name }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="resource_tag"
      :title="t('资源标签')">
      <template #default="{ row }: { row: RowData }">
        <DbTag
          v-for="labelName in row.resource_spec.redis.label_names"
          :key="labelName"
          class="mr-4">
          {{ labelName }}
        </DbTag>
        <DbTag
          v-if="!(row.resource_spec.redis.label_names || []).length"
          theme="success">
          {{ t('通用无标签') }}
        </DbTag>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import { utcDisplayTime } from '@utils';

  interface Props {
    ticketDetails: TicketModel<Redis.Rollback>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.REDIS_ROLLBACK,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  // 备份方式文案：标识前缀 BILL 为单据备份，其余为例行备份
  const getBackupTypeText = (identify: string) => (identify.startsWith('BILL') ? t('单据备份') : t('例行备份'));

  // TendisSSD / TendisPlus 有 binlog，才有「构造到」
  const hasBinlog = (clusterType: string) => /tendisssd|tendisplus/i.test(clusterType);

  // 构造范围：勾选了分片显示指定分片个数，否则为全部
  const getScopeDisplay = (row: RowData) =>
    row.shard_values.length ? t('指定分片（n 个）', { n: row.shard_values.length }) : t('全部');
</script>
