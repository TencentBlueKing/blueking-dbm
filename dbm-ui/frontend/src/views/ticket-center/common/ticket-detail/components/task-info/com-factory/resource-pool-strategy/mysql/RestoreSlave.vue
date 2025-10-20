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
    <InfoItem :label="t('主机选择方式')">
      {{ ticketDetails.details.source_type === SourceType.RESOURCE_AUTO ? t('资源池自动匹配') : t('资源池手动选择') }}
    </InfoItem>
  </InfoList>
  <BkTable
    :data="ticketDetails.details.infos"
    row-key="id">
    <TableColumn
      :min-width="220"
      :title="t('目标从库主机')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.old_nodes.old_slave[0].ip }}
      </template>
    </TableColumn>
    <TableColumn
      :min-width="220"
      :title="t('同机关联集群')">
      <template #default="{ row: data }: { row: RowData }">
        <div
          v-for="clusterId in data.cluster_ids"
          :key="clusterId"
          style="line-height: 20px">
          {{ ticketDetails.details.clusters[clusterId].immute_domain }}
        </div>
      </template>
    </TableColumn>
    <template v-if="ticketDetails.details.source_type === SourceType.RESOURCE_AUTO">
      <TableColumn
        :min-width="120"
        :title="t('目标规格')">
        <template #default="{ row }: { row: RowData }">
          {{ ticketDetails.details.specs?.[row.resource_spec.new_slave.spec_id]?.name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        :min-width="200"
        :title="t('资源标签')">
        <template #default="{ row: data }: { row: RowData }">
          <template v-if="data.resource_spec.new_slave?.label_names?.length">
            <BkTag
              v-for="item in data.resource_spec.new_slave.label_names"
              :key="item">
              {{ item }}
            </BkTag>
          </template>
          <BkTag
            v-else
            theme="success">
            {{ t('通用无标签') }}
          </BkTag>
        </template>
      </TableColumn>
    </template>
    <template v-if="ticketDetails.details.source_type === SourceType.RESOURCE_MANUAL">
      <TableColumn
        :min-width="120"
        :title="t('新从库主机')">
        <template #default="{ row: data }: { row: RowData }">
          {{ data.resource_spec.new_slave.hosts?.[0]?.ip || '--' }}
        </template>
      </TableColumn>
    </template>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('备份源')">
      {{ ticketDetails.details.backup_source === 'local' ? t('本地备份') : t('远程备份') }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';
  import { SourceType } from '@services/types';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.ResourcePool.RestoreSlave>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MYSQL_RESTORE_SLAVE,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
