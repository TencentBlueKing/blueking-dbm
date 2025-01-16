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
  <BkTable
    :data="ticketDetails.details.infos"
    :show-overflow="false">
    <BkTableColumn
      :label="t('目标集群')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        <p
          v-for="item in data.cluster_ids"
          :key="item">
          {{ ticketDetails.details.clusters[item].immute_domain }}
        </p>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('当前版本')"
      :min-width="100">
      <template #default="{ data }: { data: RowData }">
        {{ data.display_info.current_version || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('目标版本')"
      :min-width="400">
      <template #default="{ data }: { data: RowData }">
        {{ data.display_info.target_package || '--' }}
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('忽略业务连接：')">
      {{ ticketDetails.details.force ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.ProxyUpgrade>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.MYSQL_PROXY_UPGRADE,
    inheritAttrs: false,
  });

  const { t } = useI18n();
</script>
