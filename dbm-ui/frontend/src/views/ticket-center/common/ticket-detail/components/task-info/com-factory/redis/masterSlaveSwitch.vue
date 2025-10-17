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
  <PrimaryTable :data="ticketDetails.details.infos" row-key="pairs[0].redis_master">
    <TableColumn
      :min-width="200"
      :title="t('主库主机')">
      <template #default="{ row }: { row: RowData }">
        {{ row.pairs[0].redis_master }}
      </template>
    </TableColumn>
    <TableColumn
      :min-width="300"
      :title="t('所属集群')">
      <template #default="{ row }: { row: RowData }">
        <p
          v-for="item in row.cluster_ids"
          :key="item">
          {{ ticketDetails.details.clusters[item].immute_domain }}
        </p>
      </template>
    </TableColumn>
    <TableColumn :title="t('待切换的从库主机')">
      <template #default="{ row }: { row: RowData }">
        {{ row.pairs[0].redis_slave }}
      </template>
    </TableColumn>
    <TableColumn :title="t('切换模式')">
      <template #default="{ row }: { row: RowData }">
        {{ row.online_switch_type === 'user_confirm' ? t('需人工确认') : t('无需确认') }}
      </template>
    </TableColumn>
  </PrimaryTable>
  <InfoList>
    <InfoItem :label="t('是否强制切换')">
      {{ ticketDetails.details.force ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Redis.MasterSlaveSwitch>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.REDIS_MASTER_SLAVE_SWITCH,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
