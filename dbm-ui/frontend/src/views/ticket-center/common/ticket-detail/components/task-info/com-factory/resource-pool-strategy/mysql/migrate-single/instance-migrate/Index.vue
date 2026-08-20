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
  <InfoList>
    <InfoItem :label="t('迁移方式')">
      {{ t('实例迁移') }}
    </InfoItem>
    <InfoItem :label="t('迁移内容')">
      {{ restoreTypeMap[ticketDetails.details.orphan_restore_type] }}
    </InfoItem>
    <InfoList v-if="ticketDetails.details.orphan_restore_type !== 'restore_from_flow_backup'">
      <InfoItem :label="t('备份源')">
        {{ ticketDetails.details.backup_source === 'local' ? t('本地备份') : t('远程备份') }}
      </InfoItem>
    </InfoList>
  </InfoList>
  <TicketInfoTable
    :data="ticketDetails.details.infos"
    row-key="cluster_ids">
    <TicketInfoTableColumn
      col-key="cluster_ids"
      :get-copy-value="
        (item: RowData) =>
          item.cluster_ids.map((clusterId) => ticketDetails.details.clusters?.[clusterId]?.immute_domain || '')
      "
      :min-width="260"
      :title="t('目标集群')">
      <template #default="{ row }: { row: RowData }">
        <div
          v-for="clusterId in row.cluster_ids"
          :key="clusterId"
          style="line-height: 20px">
          {{ ticketDetails.details.clusters?.[clusterId]?.immute_domain || '--' }}
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="spec_id"
      :min-width="120"
      :title="t('规格')">
      <template #default="{ row: data }: { row: RowData }">
        {{ ticketDetails.details.specs?.[data.resource_spec.bk_new_orphan?.spec_id]?.name || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="label_names"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row: data }: { row: RowData }">
        <template v-if="data.resource_spec.bk_new_orphan?.label_names?.length">
          <DbTag
            v-for="item in data.resource_spec.bk_new_orphan.label_names"
            :key="item">
            {{ item }}
          </DbTag>
        </template>
        <DbTag
          v-else
          theme="success">
          {{ t('通用无标签') }}
        </DbTag>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import InfoList, { Item as InfoItem } from '../../../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.ResourcePool.MigrateSingle>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  const { t } = useI18n();

  const restoreTypeMap: Record<string, string> = {
    replicate_with_data: t('包含数据+实时同步'),
    replicate_with_struct: t('仅表结构+实时同步'),
    restore_from_flow_backup: t('仅表结构(本地实时导出)'),
  };
</script>
