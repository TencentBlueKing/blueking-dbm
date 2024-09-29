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
    <BkTableColumn :label="t('目标集群')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('源DB名')">
      <template #default="{ data }: { data: RowData }">
        <BkTag v-if="data.from_database">
          {{ data.from_database }}
        </BkTag>
        <span v-else>--</span>
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('新DB名')">
      <template #default="{ data }: { data: RowData }">
        <BkTag v-if="data.to_database">
          {{ data.to_database }}
        </BkTag>
        <span v-else>--</span>
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('忽略业务连接：')">
      {{ ticketDetails.details.force ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.RenameDataBase>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_RENAME_DATABASE,
    inheritAttrs: false,
  });

  const { t } = useI18n();
</script>
