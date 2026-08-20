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
      {{ t('故障迁移') }}
    </InfoItem>
    <InfoItem :label="t('新机所需数据')">
      {{ restoreTypeMap[ticketDetails.details.orphan_restore_type] }}
    </InfoItem>
  </InfoList>
  <TicketInfoTable
    :data="ticketDetails.details.infos"
    row-key="cluster_ids">
    <TicketInfoTableColumn
      col-key="old_orphan"
      :get-copy-value="(item: RowData) => item.old_orphan?.ip || ''"
      :min-width="260"
      :title="t('目标主机')">
      <template #default="{ row }: { row: RowData }">
        {{ row.old_orphan.ip }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="related_cluster_infos"
      :get-copy-value="
        (item: RowData) =>
          item.cluster_ids.map((clusterId) => ticketDetails.details.clusters?.[clusterId]?.immute_domain || '')
      "
      :min-width="260"
      :title="t('关联集群实例')">
      <template #default="{ row }: { row: RowData }">
        <div
          v-for="item in row.related_cluster_infos"
          :key="item.instance_address"
          style="line-height: 20px">
          <p>
            {{ item.master_domain }}
          </p>
          <p style="color: #979ba5">-- {{ item.instance_address }}</p>
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="spec_id"
      :min-width="120"
      :title="t('规格')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.specs?.[row.resource_spec.bk_new_orphan?.spec_id]?.name || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="label_names"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row }: { row: RowData }">
        <template v-if="row.resource_spec.bk_new_orphan?.label_names?.length">
          <DbTag
            v-for="item in row.resource_spec.bk_new_orphan.label_names"
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
    restore_with_data: t('包含数据'),
    restore_with_struct: t('仅表结构(最近1次远程备份)'),
  };
</script>
