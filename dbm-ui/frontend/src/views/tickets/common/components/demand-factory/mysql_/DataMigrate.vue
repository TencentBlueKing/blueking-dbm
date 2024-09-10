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
    <BkTableColumn :label="t('源集群')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.source_cluster].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('目标集群')">
      <template #default="{ data }: { data: RowData }">
        {{ getTargetClusters(data.target_clusters) }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('迁移DB名')">
      <template #default> -- </template>
    </BkTableColumn>
    <BkTableColumn :label="t('忽略DB名')">
      <template #default> -- </template>
    </BkTableColumn>
    <BkTableColumn :label="t('最终DB名')">
      <template #default="{ data }: { data: RowData }">
        {{ data?.db_list?.join(',') }}
      </template>
    </BkTableColumn></BkTable
  >
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mysql.DataMigrate>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.MYSQL_DATA_MIGRATE,
  });

  const { t } = useI18n();

  const getTargetClusters = (arr) => {
    if (!arr || !arr.length) {
      return '--';
    }
    const result = arr.map((item) => props.ticketDetails.details.clusters[item].immute_domain);
    return result?.join(',');
  };
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
