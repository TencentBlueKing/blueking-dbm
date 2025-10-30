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
    row-key="bk_cloud_id">
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
      :title="t('架构版本')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].cluster_type_name }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="master_instance"
      :title="t('待构造的实例')">
      <template #default="{ row }: { row: RowData }">
        <p
          v-for="item in row.master_instances"
          :key="item">
          {{ item }}
        </p>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="spec"
      :title="t('规格需求')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.specs[row.resource_spec.redis.spec_id].name }}
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
      col-key="recovery_time_point"
      :title="t('构造到指定时间')">
      <template #default="{ row }: { row: RowData }">
        {{ utcDisplayTime(row.recovery_time_point) }}
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
    ticketDetails: TicketModel<Redis.DataStructure>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.REDIS_DATA_STRUCTURE,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
